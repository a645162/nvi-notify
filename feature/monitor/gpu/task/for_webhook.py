from feature.config import settings, user_info
from feature.monitor import enum


class TaskInfoForWebHook:
    def __init__(self, info: dict, task_event: enum.TaskEvent) -> None:
        self._task_event: enum.TaskEvent = task_event
        self._pid: int = info.get("pid", 0)
        self._gpu_id: int = info.get("gpu_id", 0)
        self._gpu_name: str = f"[GPU:{self._gpu_id}]" if settings.NUM_GPU > 1 else "GPU"
        self._gpu_status_msg: str = info.get("gpu_status_msg", "")

        self._user: user_info.UserInfo | None = info.get("user")

        self._running_time_human: str = info.get("running_time_human", "Unknown")
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
        if self.task_event == enum.TaskEvent.CREATE:
            return self._num_task
        elif self.task_event == enum.TaskEvent.FINISH:
            return max(0, self._num_task - 1)

        return self._num_task

    @num_task.setter
    def num_task(self, value: int) -> None:
        self._num_task = value

    @property
    def task_event(self) -> enum.TaskEvent:
        return self._task_event

    @property
    def gpu_id(self) -> int:
        return self._gpu_id

    @property
    def gpu_name(self) -> str:
        return self._gpu_name

    @property
    def user(self) -> user_info.UserInfo | None:
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
    def task_msg_body(self) -> str:
        if self.task_event == enum.TaskEvent.CREATE:
            return self.task_msg_body_for_create
        elif self.task_event == enum.TaskEvent.FINISH:
            return self.task_msg_body_for_finish
        else:
            return ""

    @property
    def task_msg_body_for_create(self) -> str:
        return (
            f"🚀{self.user.name_cn}的"  # type: ignore
            f"({self.screen_name}{self.project_name}-{self.python_file})启动"
            "\n"
        )

    @property
    def task_msg_body_for_finish(self) -> str:
        return (
            f"☑️{self.user.name_cn}的"  # type: ignore
            f"({self.screen_name}{self.project_name}-{self.python_file})完成，"
            f"用时{self.running_time_human}，"
            f"最大显存{self.task_gpu_memory_max_human}"
            "\n"
        )

    @staticmethod
    def get_emoji(key: int | str) -> str:
        EMOJI_DICT = {  # noqa: N806
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
