# -*- coding: utf-8 -*-
import os
import os.path
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import psutil
from nvitop import GpuProcess

from config.settings import USERS, WEBHOOK_DELAY_SEND_SECONDS, EnvironmentManager
from config.user_info import UserInfo
from feature.group_center import group_center_message
from feature.monitor.gpu.task.for_sql import TaskInfoForSQL
from feature.monitor.gpu.task.for_webhook import TaskInfoForWebHook
from feature.monitor.monitor_enum import AllWebhookName, MsgType, TaskEvent, TaskState
from feature.notify.message_handler import MessageHandler
from feature.notify.webhook import Webhook
from feature.sql.sqlite import get_sql
from feature.utils.logs import get_logger
from feature.utils.utils import do_command

logger = get_logger()
sql = get_sql()


class GPUProcessInfo:
    def __init__(self, pid: int, gpu_id: int, gpu_process: GpuProcess) -> None:
        self.task_id: str = datetime.now().strftime("%Y%m") + str(gpu_id) + str(pid)

        self.pid: int = pid
        self.process_name: str = gpu_process.name()

        # current GPU
        self.gpu_id: int = gpu_id
        self.gpu_process: GpuProcess = gpu_process

        self.num_task: int = 0
        self.process_environ: Optional[dict[str, str]] = None

        # current process
        self.cwd: str = ""  # pwd
        self.command: str = ""
        self.cmdline: Optional[list] = None

        self.is_debug: Optional[bool] = None

        self.task_main_memory_mb: int = 0

        self.task_gpu_memory: int = 0
        self.task_gpu_memory_max: int = 0
        self.task_gpu_memory_human: str = ""

        self.user: Optional[UserInfo] = None
        self.conda_env: str = ""
        self.project_name: str = ""
        self.python_file: str = ""

        self.python_version: str = ""

        self.start_time: float = 0.0  # timestamp
        self.finish_time: float = 0.0  # timestamp
        self.running_time_human: str = ""

        # Props get from env var
        self.is_multi_gpu: bool = False
        self.world_size: int = 0
        self.local_rank: int = 0
        self.cuda_visible_devices: str = ""
        self.screen_session_name: str = ""
        self.cuda_root: str = ""
        self.cuda_nvcc_bin: str = ""
        self.cuda_version: str = ""

        self._gpu = None
        self._state: Optional[TaskState] = TaskState.DEFAULT  # init
        self._running_time_in_seconds: int = 0  # init

        self.__init_info__()

    def __init_info__(self):
        self.get_cwd()
        self.get_command()
        self.get_cmdline()
        self.get_process_environ()

        self.get_all_env()

        self.judge_is_python()

        if self.is_python:
            self.get_python_version()
            self.get_debug_flag()
            self.get_user()
            self.get_project_name()
            self.get_python_filename()
            self.get_start_time()

            self.update_gpu_process_info()

            sql.insert_task_data(TaskInfoForSQL(self.__dict__))

    def get_all_env(self):
        self.get_screen_session_name()
        self.get_conda_env_name()

        self.get_world_size()
        self.get_local_rank()
        self.get_is_multi_gpu()
        self.get_cuda_visible_devices()

        self.get_cuda_root()
        self.get_cuda_version()

    def update_gpu_process_info(self):
        self.get_task_main_memory_mb()
        self.get_task_gpu_memory_human()
        self.get_task_gpu_memory()
        self.get_running_time_human()
        self.get_running_time_in_seconds()

    @property
    def gpu(self):
        return self._gpu

    @gpu.setter
    def gpu(self, value):
        self._gpu = value

    def get_cwd(self):
        try:
            self.cwd = self.gpu_process.cwd()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # self.state = "death"
            pass

    def get_command(self):
        try:
            self.command = self.gpu_process.command()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # self.state = "death"
            pass

    def get_cmdline(self):
        try:
            self.cmdline = self.gpu_process.cmdline()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # self.state = "death"
            pass

    def get_process_environ(self):
        try:
            process = psutil.Process(self.pid)
            self.process_environ = process.environ().copy()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    def get_task_main_memory_mb(self):
        try:
            self.task_main_memory_mb = (
                self.gpu_process.memory_info().rss // 1024 // 1024
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Task Gpu Memory(Bytes)
    def get_task_gpu_memory(self):
        task_gpu_memory = self.gpu_process.gpu_memory()
        self.task_gpu_memory = task_gpu_memory

        if (
            self.task_gpu_memory_max is None
            or self.task_gpu_memory_max < task_gpu_memory
        ):
            self.task_gpu_memory_max = task_gpu_memory
            self.task_gpu_memory_max_human = self.task_gpu_memory_human

    def get_task_gpu_memory_human(self):
        self.task_gpu_memory_human = self.gpu_process.gpu_memory_human()

    def get_running_time_in_seconds(self):
        self.running_time_in_seconds = self.gpu_process.running_time_in_seconds()

    def get_running_time_human(self):
        self.running_time_human = self.gpu_process.running_time_human()

    def get_start_time(self):
        self.start_time = self.gpu_process.create_time()

    def set_finish_time(self):
        self.finish_time = datetime.timestamp(datetime.now())

    def judge_is_python(self):
        try:
            gpu_process_name = self.gpu_process.name()
        except Exception as e:
            e_str = str(e)
            if "process no longer exists" not in e_str:
                logger.warn(e)
            self.is_python = False
            return
        self.is_python = gpu_process_name in ["python", "yolo"] or any(
            "python" in cmd for cmd in self.cmdline
        )

    def get_debug_flag(self):
        if self.cmdline is None:
            self.is_debug = False
            return

        cmdline = [line for line in self.cmdline if not line.endswith("python")]
        debug_cmd_keywords = ["vscode-server", "debugpy", "pydev/pydevd.py"]
        self.is_debug = any(
            any(keyword in _unit for _unit in cmdline) for keyword in debug_cmd_keywords
        )

    def get_user(self):
        self.user = USERS.get(self.gpu_process.username(), None)

        if self.user is not None:
            return

        cwd = self.cwd + "/" if self.cwd is not None else ""
        self.user = UserInfo.find_user_by_path(USERS, cwd, is_project_path=True)

    def get_env_value(self, key: str, default_value: str):
        if self.process_environ is None:
            return default_value

        return self.process_environ.get(key, default_value)

    def get_conda_env_name(self):
        pattern = r"envs/(.*?)/bin/python "
        match = re.search(pattern, self.command)
        if match:
            conda_env_name = match.group(1)
            env_str = conda_env_name
        else:
            env_str = self.get_env_value("CONDA_DEFAULT_ENV", "")

        env_str = env_str.strip()

        if env_str == "":
            env_str = "base"

        self.conda_env = env_str

    def get_python_version(self):
        try:
            binary_path = psutil.Process(self.pid).exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # self.state = "death"
            binary_path = ""
        self.get_python_version_by_path(binary_path)

    def get_conda_python_version(self, conda_env: str) -> str:
        command = f"conda run -n {conda_env} python --version"
        python_version = self.get_python_version_by_command(command)

        self.python_version = python_version
        return python_version

    def get_python_version_by_path(self, binary_path: str) -> str:
        if "python" not in binary_path:
            self.python_version = ""

        command = f"'{binary_path}' --version"
        python_version = self.get_python_version_by_command(command)

        self.python_version = python_version
        return python_version

    def get_world_size(self):
        # 多卡任务的进程数
        world_size = self.get_env_value("WORLD_SIZE", "").strip()
        self.world_size = int(world_size) if world_size.isdigit() else 0

    def get_local_rank(self):
        # 多卡任务的卡号
        local_rank = self.get_env_value("LOCAL_RANK", "").strip()
        self.local_rank = int(local_rank) if local_rank.isdigit() else 0

    def get_is_multi_gpu(self):
        self.is_multi_gpu = self.get_local_rank() != "" and self.world_size > 1

    def get_cuda_visible_devices(self):
        self.cuda_visible_devices = self.get_env_value("CUDA_VISIBLE_DEVICES", "")

    def get_cuda_root(self):
        cuda_home = self.get_env_value("CUDA_HOME", "").strip()
        nvcc_path = os.path.join(cuda_home, "bin", "nvcc")
        if os.path.exists(nvcc_path):
            self.cuda_root = cuda_home
            self.cuda_nvcc_bin = nvcc_path
            return

        cuda_toolkit_root = self.get_env_value("CUDAToolkit_ROOT", "").strip()
        nvcc_path = os.path.join(cuda_toolkit_root, "bin", "nvcc")
        if os.path.exists(nvcc_path):
            self.cuda_root = cuda_toolkit_root
            self.cuda_nvcc_bin = nvcc_path
            return

    def get_cuda_version(self):
        if self.cuda_nvcc_bin.strip() == "" or (not os.path.exists(self.cuda_nvcc_bin)):
            return

        try:
            cmd = f"{self.cuda_nvcc_bin} --version"
            _, result, _ = do_command(cmd)

            if "release" not in result:
                return
            result_list = result.split("\n")
            version = ""

            for line in result_list:
                if "release" in line:
                    version = line.split(",")[-1].strip()
                    break

            self.cuda_version = version
        except Exception:
            return

    def get_screen_session_name(self):
        self.screen_session_name = self.get_env_value("STY", "").strip()

        if self.screen_session_name == "":
            return

        dot_index = self.screen_session_name.find(".")
        if dot_index != -1:
            name_spilt_list = self.screen_session_name.split(".")
            if len(name_spilt_list) >= 2 and name_spilt_list[0].isdigit():
                self.screen_session_name = self.screen_session_name[
                    dot_index + 1 :
                ].strip()

    def get_project_name(self):
        if self.cwd is not None:
            self.project_name = self.cwd.split("/")[-1].strip()
        else:
            self.project_name = "".strip()

    def get_python_filename(self):
        if self.cmdline is None:
            self.python_file = ""
            return

        file_name = next(
            (cmd_str for cmd_str in self.cmdline if cmd_str.lower().endswith(".py")), ""
        )
        if "/" in file_name:
            self.python_file = file_name.split("/")[-1].strip()
        else:
            self.python_file = file_name.strip()

    @property
    def running_time_in_seconds(self):
        return self._running_time_in_seconds

    @running_time_in_seconds.setter
    def running_time_in_seconds(self, new_running_time_in_seconds):
        # 上次不满足，但是这次满足
        if (
            new_running_time_in_seconds
            > WEBHOOK_DELAY_SEND_SECONDS
            > self._running_time_in_seconds
        ):
            self.state = TaskState.WORKING

        self._running_time_in_seconds = new_running_time_in_seconds

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state: TaskState.__members__):
        if not isinstance(new_state, TaskState):
            raise ValueError(
                f"new_state must be an instance of TaskState, got {new_state}"
            )

        if self._state == new_state:
            return

        if not TaskState.check_valid_transition(self._state, new_state):
            raise ValueError(
                f"Invalid state transition from {self._state} to {new_state}"
            )

        try:
            self._handle_state_change(new_state)
        except Exception as e:
            logger.error(f"Error during state change: {e}")
            raise

        self._state = new_state

    def _handle_state_change(self, new_state):
        if new_state == TaskState.NEWBORN and self._state is TaskState.DEFAULT:
            self._transition_to_newborn()
        elif new_state == TaskState.WORKING and self._state == TaskState.NEWBORN:
            self._transition_newborn_to_working()
        elif new_state == TaskState.DEATH and self._state == TaskState.WORKING:
            self._transition_working_to_death()
        elif new_state == TaskState.DEATH and self._state == TaskState.NEWBORN:
            self._transition_newborn_to_death()

    def _transition_to_newborn(self):
        log_task_info(self.__dict__, TaskEvent.CREATE)

    def _transition_newborn_to_working(self):
        sql.update_task_data(TaskInfoForSQL(self.__dict__, TaskState.WORKING))

        group_center_message.gpu_task_message(self, TaskEvent.CREATE)
        self._send_gpu_task_message(TaskEvent.CREATE)

    def _transition_working_to_death(self):
        log_task_info(self.__dict__, TaskEvent.FINISH)
        sql.update_finish_task_data(TaskInfoForSQL(self.__dict__, TaskState.DEATH))

        group_center_message.gpu_task_message(self, TaskEvent.FINISH)
        self._send_gpu_task_message(TaskEvent.FINISH)

    def _transition_newborn_to_death(self):
        log_task_info(self.__dict__, TaskEvent.FINISH)
        sql.update_finish_task_data(TaskInfoForSQL(self.__dict__, TaskState.DEATH))

    def _send_gpu_task_message(self, task_event: TaskEvent):
        """
        发送GPU任务消息函数
        :param task_event: 任务状态
        """
        task = TaskInfoForWebHook(self.__dict__, task_event)
        if task.is_debug:
            return

        # multi_gpu_msg = task.multi_gpu_msg
        # if multi_gpu_msg == "-1":  # 非第一个使用的GPU不发送消息
        #     return

        msg = MessageHandler.handle_normal_text(
            self.gpu.name_for_msg_header
            + "\n"
            + task.task_msg_body
            + self.gpu.gpu_status_msg
            + "\n"
            + self.gpu.gpu_tasks_num_msg_header
            + self.gpu.all_tasks_msg_body,
        )
        Webhook.enqueue_msg_to_webhook(
            msg,
            MsgType.NORMAL,
            task.user if task_event == TaskEvent.FINISH else None,
            enable_webhook_name=AllWebhookName.ALL,
        )

    @staticmethod
    def get_python_version_by_command(command) -> str:
        try:
            _, result, _ = do_command(command)

            if "Python" not in result:
                return ""
            result = result.replace("Python", "").strip()
            if "." in result:
                return result
            return ""
        except Exception:
            return ""


def log_task_info(process_info: dict, task_event: TaskEvent):
    """
    任务日志函数
    :param process_info: 进程信息字典
    :task_event: 任务类型, `create` or `finish`
    """
    if task_event is None:
        raise ValueError("task_event is None")

    logfile_dir_path = Path("./log")
    if not os.path.exists(logfile_dir_path):
        os.makedirs(logfile_dir_path)

    task = TaskInfoForWebHook(process_info, task_event)

    with open(logfile_dir_path / "user_task.log", "a") as log_writer:
        if task_event == TaskEvent.CREATE:
            output_log = (
                f"{task.gpu_name}"
                f" {task.user.name_cn} "
                f"create new {'debug ' if task.is_debug else ''}"
                f"task: {task.pid}"
            )
        elif task_event == TaskEvent.FINISH:
            output_log = (
                f"{task.gpu_name}"
                f" finish {task.user.name_cn}'s {'debug ' if task.is_debug else ''}"
                f"task: {task.pid}，用时{task.running_time_human}"
            )
        log_writer.write(f"[{EnvironmentManager.now_time_str()}]+{output_log} + \n")
        logger.info(output_log)
