from typing import Dict, List

import psutil
from nvitop import GpuProcess

from config import config, keywords
from monitor.send_task_info import (
    create_task_log,
    finish_task_log,
    send_gpu_task_message,
)


class PythonProcess:
    def __init__(self, pid: int, gpu_id: int, gpu_process: GpuProcess) -> None:
        self.pid: int = pid
        self.gpu_id: int = gpu_id
        self.gpu_process: GpuProcess = gpu_process
        self.gpu_status: Dict = None
        self.gpu_all_tasks_msg: str = None
        self.num_task: int = 0

        self.cwd: str = None  # pwd
        self.command: str = None
        self.cmdline: List = None

        self.is_debug: bool = None
        self.running_time_human: str = None
        self.user: Dict = None
        self.conda_env: str = None
        self.memory_usage: str = None
        self.project_name: str = None
        self.python_file: str = None

        self._state: str = None  # init
        self._running_time_in_seconds: int = None  # init

        self.__init_info__()

    def __init_info__(self):
        self.update_cmd()
        self.is_python = self.judge_is_python()
        if self.is_python:
            self.update_gpu_process_info()
            self.get_debug_flag()
            self.get_user()
            self.get_conda_env_name()
            self.project_name = self.get_project_name()
            self.python_file = self.get_python_filename()

    def update_cmd(self):
        self.get_cwd()
        self.get_command()
        self.get_cmdline()

    def update_gpu_process_info(self):
        self.get_gpu_memory_human()
        self.get_running_time_in_seconds()
        self.get_running_time_human()

    def get_cwd(self):
        try:
            self.cwd = self.gpu_process.cwd()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            self.state = "death"

    def get_command(self):
        try:
            self.command = self.gpu_process.command()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            self.state = "death"

    def get_cmdline(self):
        try:
            self.cmdline = self.gpu_process.cmdline()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # send_process_except_msg()
            self.state = "death"

    def get_gpu_memory_human(self):
        self.gpu_memory_human = self.gpu_process.gpu_memory_human()

    def get_running_time_in_seconds(self):
        self.running_time_in_seconds = self.gpu_process.running_time_in_seconds()

    def get_running_time_human(self):
        self.running_time_human = self.gpu_process.running_time_human()

    def judge_is_python(self):
        process_name = self.gpu_process.name()
        if process_name in ["python", "yolo"]:
            return True
        else:
            if any("python" in cmd for cmd in self.cmdline):
                return True

    def get_debug_flag(self):
        _cmdline = self.cmdline
        for line in _cmdline:
            if line.split("/")[-1] == "python" or line == "python":
                _cmdline.remove(line)

        debug_cmd_keywords = ["vscode-server", "debugpy", "pydev/pydevd.py"]

        if any(keyword in _cmdline[0] for keyword in debug_cmd_keywords):
            self.debug_flag = True
        else:
            self.debug_flag = False

    def get_user(self):
        user_dict = keywords.find_user_by_path(config.user_list, self.cwd + "/")

        if user_dict is None:
            user_dict = {
                "name": "Unknown",
                "keywords": [],
                "mention_id": [],
                "mention_phone_number": [],
            }
        self.user = user_dict

    def get_conda_env_name(self):
        try:
            process = psutil.Process(self.pid)

            conda_env = process.environ().get("CONDA_DEFAULT_ENV", None)

            if conda_env:
                self.conda_env = conda_env

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    def get_project_name(self):
        if self.cwd is not None:
            return self.cwd.split("/")[-1]

    def get_python_filename(self):
        for cmd_str in self.cmdline:
            if cmd_str.lower().endswith(".py"):
                if "/" in cmd_str:
                    return cmd_str.split("/")[-1]
                else:
                    # cmd_str[:-3] # remove file expanded-name
                    return cmd_str

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        state_transitions = {
            ("newborn", "death"): create_task_log,
            ("working", "newborn"): lambda data: send_gpu_task_message(data, "create"),
            ("death", "working"): lambda data: send_gpu_task_message(data, "finish"),
            ("death", "newborn"): finish_task_log,
        }

        action = state_transitions.get((new_state, self._state))
        if action:
            action(self.__dict__)

        self._state = new_state

    @property
    def running_time_in_seconds(self):
        return self._running_time_in_seconds

    @running_time_in_seconds.setter
    def running_time_in_seconds(self, new_running_time_in_seconds):
        if new_running_time_in_seconds > 300 and self._running_time_in_seconds < 300:
            self.state = "working"
        self._running_time_in_seconds = new_running_time_in_seconds
