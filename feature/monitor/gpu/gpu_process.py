import re
import typing
from datetime import datetime
from pathlib import Path

import nvitop
import psutil
from group_center.tools.user_env import realtime

from feature.config import settings, user_info
from feature.database import sqlite
from feature.group_center import message
from feature.monitor import enum
from feature.monitor.gpu.task import for_sql, for_webhook
from feature.utils import common_utils, logs, process, spawn
from feature.webhook import msg_handler, webhook

if typing.TYPE_CHECKING:
    from feature.monitor.gpu import gpu

logger = logs.get_logger()
sql = sqlite.get_sql()


def check_process_env(pid: int, env_name: str, check_parent: bool = False) -> bool:
    try:
        process = psutil.Process(pid)

        if env_name in process.environ():
            return True

        if check_parent:
            parent = process.parent()
            if parent is None:
                return False

            ppid = parent.pid

            # Stop when the parent process is the init process
            if ppid == 1:
                return False

            if check_process_env(ppid, env_name):
                return True
        return False
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False
    except Exception as e:
        logger.error(e)
        return False


class GPUProcessInfo:
    def __init__(
        self, pid: int, gpu_id: int, cur_gpu: gpu.GPU, gpu_process: nvitop.GpuProcess
    ) -> None:
        self.task_id: str = datetime.now().strftime("%Y%m") + str(gpu_id) + str(pid)

        self.pid: int = pid
        self.process_name: str = gpu_process.name()

        # Current GPU
        self.gpu: gpu.GPU = cur_gpu
        self.gpu_id: int = gpu_id
        self.gpu_process: nvitop.GpuProcess = gpu_process

        # 缓存psutil.Process对象，避免重复实例化
        self._process: psutil.Process | None = None
        self._init_process()

        self.num_task: int = 0
        self.process_environ: dict[str, str] | None = None

        # 静态信息 - 初始化时获取，不会变化
        self.cwd: str = ""
        self.command: str = ""
        self.cmdline: list[str] = [""]
        self.is_debug: bool = False
        self.user: user_info.UserInfo | None = None
        self.conda_env: str = ""
        self.project_name: str = ""
        self.python_file: str = ""
        self.python_version: str = ""
        self.start_time: float = 0.0
        self.is_python: bool = False
        self.is_multiprocessing_spawn: bool = False

        # 环境变量相关静态信息
        self.is_multi_gpu: bool = False
        self.world_size: int = 0
        self.local_rank: int = 0
        self.cuda_visible_devices: str = ""
        self.screen_session_name: str = ""
        self.cuda_root: str = ""
        self.cuda_nvcc_bin: Path = Path()
        self.cuda_version: str = ""
        self.top_python_pid: int = -1
        self.nvidia_driver_version: str = ""
        self.ignore_task: bool = False

        # 动态信息 - 需要定期更新
        self.task_main_memory_mb: int = 0
        self.task_gpu_memory: int = 0
        self.task_gpu_memory_max: int = 0
        self.task_gpu_memory_human: str = ""
        self.finish_time: float = 0.0
        self.running_time_human: str = ""
        self.cpu_percent: float = 0.0
        # self.cpu_times: Optional[dict] = None
        self.gpu_utilization: float = 0.0
        self.group_center_user_realtime_str: str = ""

        # GPU占用率监控相关
        self.consecutive_zero_gpu_count: int = 0
        self.max_consecutive_zero_count: int = settings.MAX_CONSECUTIVE_ZERO_COUNT
        self.should_send_gpu_alert: bool = False
        self.already_has_alerted_zero_gpu_usage: bool = False
        self.total_gpu_zero_alert_count: int = 0

        # CPU占用率监控相关
        self.consecutive_zero_cpu_count: int = 0
        self.should_send_cpu_alert: bool = False
        self.already_has_alerted_zero_cpu_usage: bool = False
        self.total_cpu_zero_alert_count: int = 0

        self._state: enum.TaskState = enum.TaskState.DEFAULT
        self._running_time_in_seconds: float = 0.0

        # 初始化静态信息
        self._init_static_info()

    def _init_process(self) -> None:
        """初始化psutil.Process对象"""
        try:
            self._process = psutil.Process(self.pid)

            # 初始化CPU监控，第一次调用会启动监控，第一次总为0
            self._process.cpu_percent()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            self._process = None

    def _init_static_info(self) -> None:
        """初始化静态信息 - 只在创建对象时调用一次"""
        try:
            self._get_basic_process_info()
            self._get_environment_info()
            self._judge_is_python()
            self.is_multiprocessing_spawn = spawn.is_multiprocessing_spawn(self.cmdline)

            if self.is_python:
                self._get_python_info()
                self._get_user_info()
                self._get_project_info()
                self._get_nvidia_driver_version()

                # 更新动态信息（首次）
                self.update()

                # 检查是否忽略任务
                self._update_ignore_mode()

                # 插入数据库
                sql.insert_task_data(for_sql.TaskInfoForSQL(self.__dict__))
            else:
                self.ignore_task = True
        except Exception as e:
            logger.error(f"Error initializing static info for PID {self.pid}: {e}")
            self.ignore_task = True

    def _get_basic_process_info(self) -> None:
        """获取基础进程信息"""
        try:
            self.cwd = self.gpu_process.cwd()
            self.command = self.gpu_process.command()
            self.cmdline = self.gpu_process.cmdline()
            self.start_time = self.gpu_process.create_time()

            if self._process:
                self.process_environ = self._process.environ().copy()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    def _get_environment_info(self) -> None:
        """获取环境变量相关信息"""
        self._get_conda_env_name()
        self._get_screen_session_name()
        self._get_multi_gpu_info()
        self._get_cuda_info()

    def _get_multi_gpu_info(self) -> None:
        """获取多GPU相关信息"""
        world_size = self._get_env_value("WORLD_SIZE", "").strip()
        self.world_size = int(world_size) if world_size.isdigit() else 0

        local_rank = self._get_env_value("LOCAL_RANK", "").strip()
        self.local_rank = int(local_rank) if local_rank.isdigit() else 0

        self.is_multi_gpu = (
            self._get_env_value("LOCAL_RANK", "") != "" and self.world_size > 1
        )
        self.cuda_visible_devices = self._get_env_value("CUDA_VISIBLE_DEVICES", "")

        if self.is_multi_gpu:
            try:
                self.top_python_pid = process.get_top_python_process_pid(self.pid)
            except Exception:
                self.top_python_pid = -1

    def _get_cuda_info(self) -> None:
        """获取CUDA相关信息"""
        cuda_home = self._get_env_value("CUDA_HOME", "").strip()
        if cuda_home and (Path(cuda_home) / "bin" / "nvcc").exists():
            self.cuda_root = cuda_home
            self.cuda_nvcc_bin = Path(cuda_home) / "bin" / "nvcc"
        else:
            cuda_toolkit_root = self._get_env_value("CUDAToolkit_ROOT", "").strip()
            if (
                cuda_toolkit_root
                and (Path(cuda_toolkit_root) / "bin" / "nvcc").exists()
            ):
                self.cuda_root = cuda_toolkit_root
                self.cuda_nvcc_bin = Path(cuda_toolkit_root) / "bin" / "nvcc"

        # 获取CUDA版本
        if self.cuda_nvcc_bin and Path(self.cuda_nvcc_bin).exists():
            try:
                _, result, _ = common_utils.do_command(
                    f"{self.cuda_nvcc_bin} --version"
                )
                if "release" in result:
                    for line in result.split("\n"):
                        if "release" in line:
                            version = line.split(",")[-1].strip()
                            self.cuda_version = version.strip().lower().replace("v", "")
                            break
            except Exception:
                pass

    def _get_python_info(self) -> None:
        """获取Python相关信息"""
        if self._process:
            try:
                binary_path = self._process.exe()
                if "python" in binary_path:
                    _, result, _ = common_utils.do_command(f"'{binary_path}' --version")
                    if "Python" in result:
                        self.python_version = result.replace("Python", "").strip()
            except Exception:
                pass

        # 获取调试标志
        if self.cmdline:
            cmdline = [line for line in self.cmdline if not line.endswith("python")]
            debug_keywords = ["vscode-server", "debugpy", "pydev/pydevd.py"]
            self.is_debug = any(
                any(keyword in unit for unit in cmdline) for keyword in debug_keywords
            )

    def _get_user_info(self) -> None:
        """获取用户信息"""
        self.user = settings.USERS.get(self.gpu_process.username(), None)
        if self.user is None and self.cwd:
            cwd = self.cwd + "/"
            self.user = user_info.UserInfo.find_user_by_path(
                settings.USERS, cwd, is_project_path=True
            )

    def _get_project_info(self) -> None:
        """获取项目信息"""
        if self.cwd:
            self.project_name = self.cwd.split("/")[-1].strip()

        if self.cmdline:
            file_name = next(
                (cmd for cmd in self.cmdline if cmd.lower().endswith(".py")), ""
            )
            if file_name:
                self.python_file = (
                    file_name.split("/")[-1].strip()
                    if "/" in file_name
                    else file_name.strip()
                )

    def update(self) -> None:
        """更新动态信息 - 定期调用此方法刷新状态"""
        try:
            self._update_memory_info()
            self._update_runtime_info()
            self._update_utilization_info()
            self._update_user_env()
        except Exception as e:
            logger.error(f"Error updating dynamic info for PID {self.pid}: {e}")

    def _update_memory_info(self) -> None:
        """更新内存信息"""
        try:
            if self._process:
                self.task_main_memory_mb = (
                    self._process.memory_info().rss // 1024 // 1024
                )

            self.task_gpu_memory_human = self.gpu_process.gpu_memory_human()
            task_gpu_memory = self.gpu_process.gpu_memory()
            if isinstance(task_gpu_memory, int):
                self.task_gpu_memory = task_gpu_memory

                if self.task_gpu_memory_max < task_gpu_memory:
                    self.task_gpu_memory_max = task_gpu_memory
                    self.task_gpu_memory_max_human = self.task_gpu_memory_human
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    def _update_runtime_info(self) -> None:
        """更新运行时间信息"""
        try:
            tmp = self.gpu_process.running_time_in_seconds()
            if isinstance(tmp, float):
                self.running_time_in_seconds = tmp
            self.running_time_human = self.gpu_process.running_time_human()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    def _update_utilization_info(self) -> None:
        """更新CPU和GPU利用率信息"""
        # 更新CPU利用率 - 使用非阻塞模式
        if self._process:
            try:
                # self.cpu_times = self._process.cpu_times()._asdict()
                # 使用interval=None获取非阻塞的CPU使用率
                self.cpu_percent = self._process.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                self.cpu_percent = 0.0
                # self.cpu_times = None
            except Exception as e:
                logger.error(f"Error getting CPU utilization for PID {self.pid}: {e}")
                self.cpu_percent = 0.0
                # self.cpu_times = None
        else:
            self.cpu_percent = 0.0
            # self.cpu_times = None

        # 更新GPU利用率
        try:
            if hasattr(self.gpu_process, "gpu_sm_utilization"):
                util = self.gpu_process.gpu_sm_utilization
                if isinstance(util, int):
                    self.gpu_utilization = util() if callable(util) else util
            else:
                self.gpu_utilization = 0.0
        except Exception as e:
            logger.error(f"Error getting GPU utilization for PID {self.pid}: {e}")
            self.gpu_utilization = 0.0

    def _update_user_env(self) -> None:
        """更新用户环境信息"""
        try:
            self.group_center_user_realtime_str = realtime.show_realtime_str(self.pid)
        except Exception as e:
            logger.error(f"Error updating user env for PID {self.pid}: {e}")

    def _get_env_value(self, key: str, default_value: str = "") -> str:
        """获取环境变量值"""
        if self.process_environ is None:
            return default_value
        return self.process_environ.get(key, default_value)

    def _judge_is_python(self) -> None:
        """判断是否为Python进程"""
        try:
            gpu_process_name = self.gpu_process.name()
            self.is_python = gpu_process_name in ["python", "yolo"] or any(
                "python" in cmd for cmd in self.cmdline
            )
        except Exception as e:
            if "process no longer exists" not in str(e):
                logger.warning(e)
            self.is_python = False

    def _get_conda_env_name(self) -> None:
        """获取conda环境名"""
        pattern = r"envs/(.*?)/bin/python "
        match = re.search(pattern, self.command)
        if match:
            self.conda_env = match.group(1)
        else:
            env_str = self._get_env_value("CONDA_DEFAULT_ENV", "").strip()
            self.conda_env = env_str if env_str else "base"

    def _get_screen_session_name(self) -> None:
        """获取screen会话名"""
        self.screen_session_name = self._get_env_value("STY", "").strip()
        if self.screen_session_name and "." in self.screen_session_name:
            parts = self.screen_session_name.split(".")
            if len(parts) >= 2 and parts[0].isdigit():
                self.screen_session_name = ".".join(parts[1:]).strip()

    def _get_nvidia_driver_version(self) -> str:
        """获取NVIDIA驱动版本"""
        try:
            with Path.open(Path("/proc/driver/nvidia/version"), "r") as f:
                content = f.read()
            match = re.search(r"Kernel Module {2}(\d+\.\d+\.\d+)", content)
            if match:
                self.nvidia_driver_version = match.group(1).strip()
                return self.nvidia_driver_version
        except Exception:
            pass
        return ""

    def _update_ignore_mode(self) -> None:
        """更新忽略模式"""
        try:
            self.ignore_task = check_process_env(
                pid=self.pid, env_name="NVI_NOTIFY_IGNORE_TASK", check_parent=True
            )
        except Exception as e:
            logger.error(e)

    @property
    def running_time_in_seconds(self) -> float:
        return self._running_time_in_seconds

    @running_time_in_seconds.setter
    def running_time_in_seconds(self, new_running_time_in_seconds: float) -> None:
        if (
            new_running_time_in_seconds
            > settings.WEBHOOK_DELAY_SEND_SECONDS
            > self._running_time_in_seconds
        ):
            self.state = enum.TaskState.WORKING
        self._running_time_in_seconds = new_running_time_in_seconds

    @property
    def state(self) -> enum.TaskState:
        return self._state

    @state.setter
    def state(self, new_state: enum.TaskState) -> None:
        if self._state == new_state:
            return

        if not enum.TaskState.check_valid_transition(self._state, new_state):
            raise ValueError(
                f"Invalid state transition from {self._state} to {new_state}"
            )

        try:
            self._handle_state_change(new_state)
        except Exception as e:
            logger.error(f"Error during state change: {e}")
            raise

        self._state = new_state

    def set_finish_time(self) -> None:
        """设置结束时间"""
        self.finish_time = datetime.timestamp(datetime.now())

    # 零占用率监控相关方法
    def check_consecutive_zero_gpu_usage(self) -> bool:
        """检查连续GPU零占用率，返回True表示需要发送报警"""
        if self.gpu_utilization == 0.0:
            self.consecutive_zero_gpu_count += 1
            # print(
            #     f"[{self.pid}]Consecutive zero GPU count: {self.consecutive_zero_gpu_count}"
            # )
            if self.consecutive_zero_gpu_count >= self.max_consecutive_zero_count:
                self.should_send_gpu_alert = True
                self.already_has_alerted_zero_gpu_usage = True
                self.total_gpu_zero_alert_count += 1
                self.consecutive_zero_gpu_count = 0
                # print(
                #     f"[{self.pid}]Total GPU zero alert count: {self.total_gpu_zero_alert_count}"
                # )
                return True
        else:
            self.consecutive_zero_gpu_count = 0
            self.should_send_gpu_alert = False
        return False

    def check_consecutive_zero_cpu_usage(self) -> bool:
        """检查连续CPU零占用率，返回True表示需要发送报警"""
        # print(f"[{self.pid}]Current CPU percent: {self.cpu_percent}")  # 调试用

        if self.cpu_percent < 1.0:  # 容忍极小波动
            self.consecutive_zero_cpu_count += 1
            # print(
            #     f"[{self.pid}]Consecutive zero CPU count: {self.consecutive_zero_cpu_count}"
            # )
            if self.consecutive_zero_cpu_count >= self.max_consecutive_zero_count:
                self.should_send_cpu_alert = True
                self.already_has_alerted_zero_cpu_usage = True
                self.total_cpu_zero_alert_count += 1
                # print(
                #     f"[{self.pid}]Total CPU zero alert count: {self.total_cpu_zero_alert_count}"
                # )
                self.consecutive_zero_cpu_count = 0
                return True
        else:
            self.consecutive_zero_cpu_count = 0
            self.should_send_cpu_alert = False
        return False

    def should_send_zero_usage_alert(self) -> dict:
        """检查是否需要发送零占用率报警"""
        return {
            "should_send_gpu_alert": self.check_consecutive_zero_gpu_usage(),
            "should_send_cpu_alert": self.check_consecutive_zero_cpu_usage(),
        }

    def reset_zero_usage_alert(self) -> None:
        """重置零占用率报警状态"""
        self.consecutive_zero_gpu_count = 0
        self.should_send_gpu_alert = False
        self.consecutive_zero_cpu_count = 0
        self.should_send_cpu_alert = False

    # 状态转换处理
    def _handle_state_change(self, new_state: enum.TaskState) -> None:
        if (
            new_state == enum.TaskState.NEWBORN
            and self._state is enum.TaskState.DEFAULT
        ):
            self._transition_to_newborn()
        elif (
            new_state == enum.TaskState.WORKING
            and self._state == enum.TaskState.NEWBORN
        ):
            self._transition_newborn_to_working()
        elif (
            new_state == enum.TaskState.DEATH and self._state == enum.TaskState.WORKING
        ):
            self._transition_working_to_death()
        elif (
            new_state == enum.TaskState.DEATH and self._state == enum.TaskState.NEWBORN
        ):
            self._transition_newborn_to_death()

    def _transition_to_newborn(self) -> None:
        logger.info(f"Task {self.pid} is created.")
        if self.ignore_task:
            logger.info(f"[Create] Task {self.pid} is ignored.")
        log_task_info(self.__dict__, enum.TaskEvent.CREATE)

    def _transition_newborn_to_working(self) -> None:
        sql.update_task_data(
            for_sql.TaskInfoForSQL(self.__dict__, enum.TaskState.WORKING)
        )
        if self.ignore_task:
            logger.info(f"[Start] Task {self.pid} is ignored.")
            return
        message.gpu_task_message(self, enum.TaskEvent.CREATE)
        self._send_gpu_task_message(enum.TaskEvent.CREATE)

    def _transition_working_to_death(self) -> None:
        log_task_info(self.__dict__, enum.TaskEvent.FINISH)
        sql.update_finish_task_data(
            for_sql.TaskInfoForSQL(self.__dict__, enum.TaskState.DEATH)
        )
        if self.ignore_task:
            logger.info(f"[Finish] Task {self.pid} is ignored.")
            return
        message.gpu_task_message(self, enum.TaskEvent.FINISH)
        self._send_gpu_task_message(enum.TaskEvent.FINISH)

    def _transition_newborn_to_death(self) -> None:
        log_task_info(self.__dict__, enum.TaskEvent.FINISH)
        sql.update_finish_task_data(
            for_sql.TaskInfoForSQL(self.__dict__, enum.TaskState.DEATH)
        )

    def _send_gpu_task_message(self, task_event: enum.TaskEvent) -> None:
        """发送GPU任务消息函数"""
        task = for_webhook.TaskInfoForWebHook(self.__dict__, task_event)
        if task.is_debug:
            return

        msg = msg_handler.MessageHandler.handle_normal_text(
            self.gpu.name_for_msg_header
            + "\n"
            + task.task_msg_body
            + self.gpu.gpu_status_msg
            + "\n"
            + self.gpu.gpu_tasks_num_msg_header
            + self.gpu.all_tasks_msg_body,
        )
        webhook.Webhook.enqueue_msg_to_webhook(
            msg,
            enum.MsgType.NORMAL,
            task.user if task_event == enum.TaskEvent.FINISH else None,
            enable_webhook_name=enum.AllWebhookName.ALL,
        )

    @staticmethod
    def format_duration(total_seconds: int) -> str:
        """将秒数转换为人类可读的时间格式"""
        if total_seconds < 60:
            return f"{total_seconds}秒"

        minutes = total_seconds // 60
        if minutes < 60:
            remaining_seconds = total_seconds % 60
            return (
                f"{minutes}分钟{remaining_seconds}秒"
                if remaining_seconds > 0
                else f"{minutes}分钟"
            )

        hours = minutes // 60
        if hours < 24:
            remaining_minutes = minutes % 60
            return (
                f"{hours}小时{remaining_minutes}分钟"
                if remaining_minutes > 0
                else f"{hours}小时"
            )

        days = hours // 24
        remaining_hours = hours % 24
        return f"{days}天{remaining_hours}小时" if remaining_hours > 0 else f"{days}天"


def log_task_info(process_info: dict, task_event: enum.TaskEvent) -> None:
    """任务日志函数"""
    if task_event is None:
        raise ValueError("task_event is None")

    logfile_dir_path = Path("./log")
    if not logfile_dir_path.exists():
        Path.mkdir(logfile_dir_path)

    task = for_webhook.TaskInfoForWebHook(process_info, task_event)

    with Path.open(logfile_dir_path / "user_task.log", "a") as log_writer:
        if task_event == enum.TaskEvent.CREATE:
            output_log = (
                f"{task.gpu_name}"
                f" {task.user.name_cn} "  # type: ignore
                f"create new {'debug ' if task.is_debug else ''}"
                f"task: {task.pid}"
            )
        elif task_event == enum.TaskEvent.FINISH:
            output_log = (
                f"{task.gpu_name}"
                f" finish {task.user.name_cn}'s {'debug ' if task.is_debug else ''}"  # type: ignore
                f"task: {task.pid}，用时{task.running_time_human}"
            )
        log_writer.write(
            f"[{settings.EnvironmentManager.now_time_str()}]+{output_log} + \n"
        )
        logger.info(output_log)
