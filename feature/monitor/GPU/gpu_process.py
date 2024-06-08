# -*- coding: utf-8 -*-

import os.path
import re
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

import psutil
from nvitop import GpuProcess

from config.settings import USERS, WEBHOOK_DELAY_SEND_SECONDS
from config.user.user_info import UserInfo
from feature.monitor.info.program_enum import TaskEvent, TaskState
from feature.monitor.info.gpu_info import GPUInfo
from feature.monitor.info.sql_task_info import TaskInfoForSQL
from feature.group_center import group_center
from feature.notify.send_task_msg import log_task_info, send_gpu_task_message
from utils.converter import get_human_str_from_byte
from utils.logs import get_logger
from utils.sqlite import get_sql

logger = get_logger()
sql = get_sql()


class GPUProcessInfo:
    def __init__(self, pid: int, gpu_id: int, gpu_process: GpuProcess) -> None:
        self.task_id: str = datetime.now().strftime("%Y%m") + str(gpu_id) + str(pid)

        self.pid: int = pid
        self.process_name: str = gpu_process.name()

        # current GPU
        self.gpu_id: int = gpu_id
        self.gpu_name: str = gpu_process.device.name()

        self.gpu_process: GpuProcess = gpu_process
        self.gpu_status: Optional[GPUInfo] = None
        self.gpu_all_tasks_msg: Optional[Dict] = None
        self.num_task: int = 0
        self.process_environ: Optional[dict[str, str]] = None

        # current process
        self.cwd: Optional[str] = None  # pwd
        self.command: Optional[str] = None
        self.cmdline: Optional[List] = None

        self.is_debug: Optional[bool] = None

        self.task_main_memory_mb: int = 0

        self.task_gpu_memory: Optional[int] = None
        self.task_gpu_memory_max: Optional[int] = None
        self.task_gpu_memory_human: Optional[str] = None

        self.user: Optional[UserInfo] = None
        self.conda_env: Optional[str] = None
        self.project_name: Optional[str] = None
        self.python_file: Optional[str] = None

        self.python_version: str = ""

        self.start_time: Optional[float] = None  # timestamp
        self.finish_time: Optional[float] = None  # timestamp
        self.running_time_human: Optional[str] = None

        # Props get from env var
        self.is_multi_gpu: bool = False
        self.world_size: int = 0
        self.local_rank: int = 0
        self.cuda_visible_devices: str = ""
        self.screen_session_name: str = ""
        self.cuda_root: str = ""
        self.cuda_nvcc_bin: str = ""
        self.cuda_version: str = ""

        self._state: Optional[TaskState] = TaskState.DEFAULT  # init
        self._running_time_in_seconds: int = 0  # init

        self.__init_info__()

    def __init_info__(self):
        self.get_cmd()
        self.get_all_env()
        self.judge_is_python()

        if self.is_python:
            self.update_gpu_process_info()
            self.get_debug_flag()
            self.get_user()

            self.get_project_name()
            self.get_python_filename()
            self.get_start_time()

            sql.insert_task_data(TaskInfoForSQL(self.__dict__))

    def get_cmd(self):
        self.get_cwd()
        self.get_command()
        self.get_cmdline()
        self.get_python_version()
        self.get_process_environ()
        self.get_task_main_memory_mb()

    def update_gpu_process_info(self):
        self.get_task_gpu_memory()
        self.get_task_gpu_memory_human()
        self.get_running_time_in_seconds()
        self.get_running_time_human()

    def get_all_env(self):
        self.get_screen_session_name()
        self.get_conda_env_name()

        self.get_world_size()
        self.get_local_rank()
        self.get_is_multi_gpu()
        self.get_cuda_visible_devices()

        self.get_cuda_root()
        self.get_cuda_version()

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
        task_main_memory_mb = self.gpu_process.memory_info().rss // 1024 // 1024
        self.task_main_memory_mb = task_main_memory_mb

    # Task Gpu Memory(Bytes)
    def get_task_gpu_memory(self):
        task_gpu_memory = self.gpu_process.gpu_memory()
        self.task_gpu_memory = task_gpu_memory

        if (
            self.task_gpu_memory_max is None
            or self.task_gpu_memory_max < task_gpu_memory
        ):
            self.task_gpu_memory_max = task_gpu_memory
            self.task_gpu_memory_max_human = get_human_str_from_byte(
                self.task_gpu_memory_max
            )

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

        def find_user_by_path(users: dict, path: str):
            for path_unit in reversed(path.split("data")[1].split("/")):
                if len(path_unit) == 0:
                    continue
                for user in users.values():
                    if any(
                        path_unit.lower() == keyword.lower().strip()
                        for keyword in user.keywords
                    ):
                        return user
            raise RuntimeWarning("未获取到任务用户名")

        if self.user is None:
            cwd = self.cwd + "/" if self.cwd is not None else ""
            self.user = find_user_by_path(USERS, cwd)

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
        python_version = self.get_python_version_by_path(binary_path)
        self.python_version = python_version

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
            result = subprocess.run(
                f"{self.cuda_nvcc_bin} --version",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            result = str(result.stdout)
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
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state: TaskState.__members__):
        if self._state == new_state:
            return

        if new_state == TaskState.NEWBORN and self._state is None:
            # 新生进程

            log_task_info(self.__dict__, TaskEvent.CREATE)
        elif (
            new_state == TaskState.WORKING
            and self._state == TaskState.NEWBORN
        ):
            # 新生进程进入正常工作状态

            sql.update_task_data(TaskInfoForSQL(self.__dict__, new_state))

            # Group Center
            group_center.gpu_task_message(self, TaskEvent.CREATE)

            # WebHook
            send_gpu_task_message(self.__dict__, TaskEvent.CREATE)
        elif (
            new_state == TaskState.DEATH
            and self._state == TaskState.WORKING
        ):
            # 已经进入正常工作状态的进程正常结束

            log_task_info(self.__dict__, TaskEvent.FINISH)
            sql.update_finish_task_data(TaskInfoForSQL(self.__dict__, new_state))

            # Group Center
            group_center.gpu_task_message(self, TaskEvent.FINISH)

            # WebHook
            send_gpu_task_message(self.__dict__, TaskEvent.FINISH)
        elif (
            new_state == TaskState.DEATH
            and self._state == TaskState.NEWBORN
        ):
            # 没有到发信阈值就被杀死的进程

            log_task_info(self.__dict__, TaskEvent.FINISH)
            sql.update_finish_task_data(TaskInfoForSQL(self.__dict__, new_state))

        self._state = new_state

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

    @staticmethod
    def get_conda_python_version(conda_env: str) -> str:
        try:
            command = f"conda run -n {conda_env} python --version"
            result = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            result = str(result.stdout)
            if "Python" not in result:
                return ""
            result = result.replace("Python", "").strip()
            if "." in result:
                return result
            return ""
        except Exception:
            return ""

    @staticmethod
    def get_python_version_by_path(binary_path: str) -> str:
        if "python" not in binary_path:
            return ""

        try:
            command = f"'{binary_path}' --version"
            result = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            result = str(result.stdout)
            if "Python" not in result:
                return ""
            result = result.replace("Python", "").strip()
            if "." in result:
                return result
            return ""
        except Exception:
            return ""
