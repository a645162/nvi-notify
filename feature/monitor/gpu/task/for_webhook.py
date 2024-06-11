from typing import Optional, Union

from config.settings import NUM_GPU
from config.user.user_info import UserInfo
from feature.monitor.gpu.gpu import GPUInfo
from feature.monitor.monitor_enum import TaskEvent


class TaskInfoForWebHook:
    def __init__(self, info: dict, task_event: TaskEvent) -> None:
        self._task_event: TaskEvent = task_event
        self._pid: int = info.get("pid", 0)
        self._gpu_id: int = info.get("gpu_id", 0)
        self._gpu_name: str = f"[GPU:{self._gpu_id}]" if NUM_GPU > 1 else "GPU"
        self._gpu_status: GPUInfo = info.get("gpu_status")
        self._all_task_msg: dict = info.get("gpu_all_tasks_msg_dict", {})

        self._user: UserInfo = info.get("user")

        self._running_time_human: Optional[str] = info.get("running_time_human")
        self._task_gpu_memory_max_human: str = info.get(
            "task_gpu_memory_max_human", "0MiB"
        )

        self._is_debug: bool = info.get("is_debug", True)
        self._is_multi_gpu: bool = info.get("is_multi_gpu", False)
        self._world_size: int = info.get("world_size", 1)
        self._local_rank: int = info.get("local_rank", 0)

        self._screen_name: str = info.get("screen_session_name", "")
        self._project_name: str = info.get("project_name", "Unknown")
        self._python_file: str = info.get("python_file", "Unknown")

        self._num_task: int = info.get("num_task", 0)

    @property
    def pid(self) -> int:
        return self._pid

    @property
    def num_task(self) -> int:
        if self.task_event == TaskEvent.CREATE:
            return self._num_task
        elif self.task_event == TaskEvent.FINISH:
            return max(0, self._num_task - 1)

        return self._num_task

    @num_task.setter
    def num_task(self, value):
        self._num_task = value

    @property
    def task_event(self) -> str:
        return self._task_event

    @property
    def gpu_id(self) -> int:
        return self._gpu_id

    @property
    def gpu_name(self) -> str:
        return self._gpu_name

    @property
    def gpu_status(self) -> GPUInfo:
        return self._gpu_status

    @property
    def gpu_status_msg(self) -> str:
        return (
            f"🌀{self.gpu_name}核心占用: {self.gpu_status.utl}%\n"
            f"🌀{self.gpu_name}显存占用: {self.gpu_status.mem_usage}/{self.gpu_status.mem_total} "
            f"({self.gpu_status.mem_percent}%)，{self.gpu_status.mem_free}空闲\n\n"
        )

    @property
    def user(self) -> UserInfo:
        return self._user

    @property
    def running_time_human(self) -> str:
        return self._running_time_human

    @property
    def task_gpu_memory_max_human(self) -> str:
        return self._task_gpu_memory_max_human

    @property
    def is_debug(self) -> bool:
        return self._is_debug

    @property
    def is_multi_gpu(self) -> bool:
        return self._is_multi_gpu

    @property
    def local_rank(self) -> int:
        return self._local_rank

    @property
    def world_size(self) -> int:
        return self._world_size

    @property
    def multi_gpu_msg(self) -> str:
        if self.world_size > 1:
            if self.local_rank == 0:
                return f"{self.world_size}卡任务"
            return "-1"
        return ""

    @property
    def screen_name(self) -> str:
        return (
            f"[{self._screen_name}]"
            if len(self._screen_name) > 0
            else self._screen_name
        )

    @property
    def project_name(self) -> str:
        return self._project_name

    @property
    def python_file(self) -> str:
        return self._python_file

    @property
    def all_task_msg(self) -> str:
        if len(self._all_task_msg) == 0:
            return ""
        else:
            temp_str = "".join(self._all_task_msg.values())
            return f"{temp_str}"

    @staticmethod
    def get_emoji(key: Union[int, str]) -> str:
        EMOJI_DICT = {
            0: "0️⃣",
            1: "1️⃣",
            2: "2️⃣",
            3: "3️⃣",
            4: "4️⃣",
            5: "5️⃣",
            6: "6️⃣",
            7: "7️⃣",
            8: "8️⃣",
            9: "9️⃣",
            10: "🔟",
            "呲牙": "/::D",
        }
        if key not in EMOJI_DICT.keys():
            return "Unknown Emoji"
        return EMOJI_DICT[key]
