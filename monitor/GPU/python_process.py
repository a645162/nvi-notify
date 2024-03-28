from typing import Dict, List, Optional

import psutil
from nvitop import GpuProcess

from config.config import all_valid_user_list, delay_send_seconds
from webhook.send_task_msg import (
    create_task_log,
    finish_task_log,
    send_gpu_task_message,
)


class PythonGPUProcess:
    # Enum
    NEWBORN = "newborn"
    WORKING = "working"
    DEATH = "death"

    def __init__(self, pid: int, gpu_id: int, gpu_process: GpuProcess) -> None:
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
        self.running_time_human: Optional[str] = None
        self.task_gpu_memory: Optional[int] = None
        self.task_gpu_memory_human: Optional[str] = None
        self.user: Optional[Dict] = None
        self.conda_env: Optional[str] = None
        self.project_name: Optional[str] = None
        self.python_file: Optional[str] = None

        self.start_time: Optional[float] = None

        # Props get from env var
        self.is_multi_gpu: Optional[bool] = None
        self.world_size: Optional[int] = None
        self.local_rank: Optional[int] = None
        self.cuda_visible_devices: Optional[str] = None

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

            self.get_all_env()

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

    # Task Memory(Bytes)
    def get_task_gpu_memory(self) -> int:
        task_gpu_memory = self.gpu_process.gpu_memory()
        self.task_gpu_memory = task_gpu_memory
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
            if not (
                    "process no longer exists" in e_str
            ):
                print(e)
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
        self.is_debug = any(keyword in cmdline[0] for keyword in debug_cmd_keywords)

    def get_user(self):
        self.user = next(
            (
                user
                for user in all_valid_user_list
                if self.gpu_process.username == user["name"]
            ),
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
            for user in user_list:
                if any(
                        keyword.lower().strip() in path.lower()
                        for keyword in user["keywords"]
                ):
                    return user
            return None

        cwd = self.cwd + "/" if self.cwd is not None else ""
        self.user = find_user_by_path(all_valid_user_list, cwd) or default_user_dict

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

    def get_conda_env_name(self) -> str:
        env_str = self.get_env_value("CONDA_DEFAULT_ENV", "")

        self.conda_env = env_str
        return env_str

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
                self.get_world_size() is not None
                and
                self.get_local_rank() != ""
                and
                int(self.get_world_size()) > 1
        )
        return self.is_multi_gpu

    def get_cuda_visible_devices(self) -> str:
        return self.get_env_value("CUDA_VISIBLE_DEVICES", "")

    def get_all_env(self):
        self.get_conda_env_name()
        self.get_world_size()
        self.get_local_rank()
        self.get_is_multi_gpu()
        self.get_cuda_visible_devices()

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
            create_task_log(self.__dict__)
        elif new_state == "working" and self._state == "newborn":
            send_gpu_task_message(self.__dict__, "create")
        elif new_state == "death" and self._state == "working":
            finish_task_log(self.__dict__)
            send_gpu_task_message(self.__dict__, "finish")
        elif new_state == "death" and self._state == "newborn":
            finish_task_log(self.__dict__)
        self._state = new_state

    @property
    def running_time_in_seconds(self):
        return self._running_time_in_seconds

    @running_time_in_seconds.setter
    def running_time_in_seconds(self, new_running_time_in_seconds):
        if (
                new_running_time_in_seconds
                > delay_send_seconds
                > self._running_time_in_seconds
        ):
            self.state = "working"
        self._running_time_in_seconds = new_running_time_in_seconds
