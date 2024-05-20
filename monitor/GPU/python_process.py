# -*- coding: utf-8 -*-

import re
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

import psutil
from nvitop import GpuProcess

from config.settings import USER_LIST, WEBHOOK_DELAY_SEND_SECONDS
from monitor.GPU.info import TASK_INFO_FOR_SQL, get_human_str_from_byte
from utils.logs import get_logger
from utils.sqlite import get_sql
from webhook.send_task_msg import log_task_info, send_gpu_task_message

logger = get_logger()
sql = get_sql()


class PythonGPUProcess:
    # Enum
    NEWBORN = "newborn"
    WORKING = "working"
    DEATH = "death"

    def __init__(self, pid: int, gpu_id: int, gpu_process: GpuProcess) -> None:
        self.task_task_id: str = (
            datetime.now().strftime("%Y%m") + str(gpu_id) + str(pid)
        )
        self.pid: int = pid

        # current GPU
        self.gpu_id: int = gpu_id
        self.gpu_process: GpuProcess = gpu_process
        self.gpu_status: Optional[Dict] = None
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

        self.user: Optional[Dict] = None
        self.conda_env: Optional[str] = None
        self.project_name: Optional[str] = None
        self.python_file: Optional[str] = None

        self.python_version: str = ""
        self.binary_path: str = ""

        self.start_time: Optional[float] = None  # timestamp
        self.running_time_human: Optional[str] = None

        # Props get from env var
        self.is_multi_gpu: bool = False
        self.world_size: int = 0
        self.local_rank: int = 0
        self.cuda_visible_devices: str = ""
        self.screen_session_name: str = ""

        self._state: Optional[str] = None  # init
        self._running_time_in_seconds: int = 0  # init

        self.__init_info__()

    def __init_info__(self):
        self.update_cmd()

        self.is_python = self.judge_is_python()
        if self.is_python:
            self.update_gpu_process_info()
            self.get_debug_flag()
            self.get_user()

            self.project_name = self.get_project_name()
            self.python_file = self.get_python_filename()
            self.start_time = self.gpu_process.create_time()

            self.get_task_main_memory_mb()

            self.get_all_env()

            psu_process = psutil.Process(self.pid)
            self.binary_path = psu_process.exe()

            self.update_python_version()
            sql.insert_task_data(TASK_INFO_FOR_SQL(self.__dict__))

    def update_cmd(self):
        self.get_cwd()
        self.get_command()
        self.get_cmdline()

    def update_gpu_process_info(self):
        self.get_task_gpu_memory()
        self.get_task_gpu_memory_human()
        self.get_running_time_in_seconds()
        self.get_running_time_human()

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

    # Task Main Memory(Bytes)
    def get_task_main_memory(self) -> int:
        return self.gpu_process.memory_info().rss

    def get_task_main_memory_mb(self) -> int:
        task_main_memory_mb = self.get_task_main_memory() // 1024 // 1024
        self.task_main_memory_mb = task_main_memory_mb
        return task_main_memory_mb

    # Task Gpu Memory(Bytes)
    def get_task_gpu_memory(self) -> int:
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

        return task_gpu_memory

    def get_task_gpu_memory_human(self):
        self.task_gpu_memory_human = self.gpu_process.gpu_memory_human()

    def get_running_time_in_seconds(self):
        self.running_time_in_seconds = self.gpu_process.running_time_in_seconds()

    def get_running_time_human(self):
        self.running_time_human = self.gpu_process.running_time_human()

    def judge_is_python(self):
        try:
            gpu_process_name = self.gpu_process.name()
        except Exception as e:
            e_str = str(e)
            if "process no longer exists" not in e_str:
                logger.warn(e)
            return False
        return gpu_process_name in ["python", "yolo"] or any(
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
        self.user = next(
            (user for user in USER_LIST if self.gpu_process.username == user["name"]),
            None,
        )

        default_user_dict = {
            "name": "Unknown",
            "keywords": [],
            "wework": {
                "mention_id": [],
                "mention_mobile": [],
            },
        }

        def find_user_by_path(user_list: list, path: str):
            for path_unit in reversed(path.split("data")[1].split("/")):
                if len(path_unit) == 0:
                    continue
                for user in user_list:
                    if any(
                        path_unit.lower() == keyword.lower().strip()
                        for keyword in user["keywords"]
                    ):
                        return user
            return None

        cwd = self.cwd + "/" if self.cwd is not None else ""
        self.user = find_user_by_path(USER_LIST, cwd) or default_user_dict

    def get_process_environ(self):
        try:
            process = psutil.Process(self.pid)
            self.process_environ = process.environ().copy()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    def get_env_value(self, key: str, default_value: str):
        if self.process_environ is None:
            self.get_process_environ()

        if self.process_environ is None:
            return default_value

        return self.process_environ.get(key, default_value)

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

    def get_conda_env_name(self) -> str:
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
        return env_str

    def update_python_version(self):
        python_version = self.get_python_version_by_path(self.binary_path)
        self.python_version = python_version

    # 多卡任务的进程数
    def get_world_size(self) -> int:
        env_str = self.get_env_value("WORLD_SIZE", "").strip()

        return_value = 0
        if env_str.isdigit():
            return_value = int(env_str)

        self.world_size = return_value
        return return_value

    # 多卡任务的卡号
    def get_local_rank(self) -> int:
        env_str = self.get_env_value("LOCAL_RANK", "").strip()

        return_value = 0
        if env_str.isdigit():
            return_value = int(env_str)

        self.local_rank = return_value
        return return_value

    def get_is_multi_gpu(self) -> bool:
        self.is_multi_gpu = (
            (self.get_world_size() is not None)
            and self.get_local_rank() != ""
            and int(self.get_world_size()) > 1
        )

        return self.is_multi_gpu

    def get_cuda_visible_devices(self) -> str:
        self.cuda_visible_devices = self.get_env_value("CUDA_VISIBLE_DEVICES", "")
        return self.cuda_visible_devices

    def get_screen_session_name(self) -> str:
        self.screen_session_name = self.get_env_value("STY", "").strip()

        if self.screen_session_name == "":
            return ""

        dot_index = self.screen_session_name.find(".")
        if dot_index != -1:
            name_spilt_list = self.screen_session_name.split(".")
            if len(name_spilt_list) >= 2 and name_spilt_list[0].isdigit():
                self.screen_session_name = self.screen_session_name[dot_index + 1 :]

        return self.screen_session_name

    def get_all_env(self):
        self.get_conda_env_name()
        self.get_world_size()
        self.get_local_rank()
        self.get_is_multi_gpu()
        self.get_cuda_visible_devices()
        self.get_screen_session_name()

    def get_project_name(self) -> str:
        if self.cwd is not None:
            return self.cwd.split("/")[-1]

    def get_python_filename(self) -> str:
        if self.cmdline is None:
            return ""

        file_name = next(
            (cmd_str for cmd_str in self.cmdline if cmd_str.lower().endswith(".py")), ""
        )
        return file_name.split("/")[-1] if "/" in file_name else file_name

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        if new_state == "newborn" and self._state is None:
            log_task_info(self.__dict__, task_type="create")
        elif new_state == "working" and self._state == "newborn":
            sql.update_task_data(TASK_INFO_FOR_SQL(self.__dict__, new_state))
            send_gpu_task_message(self.__dict__, "create")
        elif new_state == "death" and self._state == "working":
            log_task_info(self.__dict__, task_type="finish")
            sql.update_finish_task_data(TASK_INFO_FOR_SQL(self.__dict__, new_state))
            send_gpu_task_message(self.__dict__, "finish")
        elif new_state == "death" and self._state == "newborn":
            log_task_info(self.__dict__, task_type="finish")
            sql.update_finish_task_data(TASK_INFO_FOR_SQL(self.__dict__, new_state))
        self._state = new_state

    @property
    def running_time_in_seconds(self):
        return self._running_time_in_seconds

    @running_time_in_seconds.setter
    def running_time_in_seconds(self, new_running_time_in_seconds):
        if (
            new_running_time_in_seconds
            >= WEBHOOK_DELAY_SEND_SECONDS
            >= self._running_time_in_seconds
        ):
            self.state = "working"
        self._running_time_in_seconds = new_running_time_in_seconds
