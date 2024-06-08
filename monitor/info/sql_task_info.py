from typing import Dict, Optional

from monitor.info.enum import TaskState


class TaskInfoForSQL:
    def __init__(self, info: Dict, new_state: Optional[TaskState] = None) -> None:
        self._task_idx: str = info.get("task_id", "Unknown")
        self._pid: int = info.get("pid", 0)
        self._gpu_id: int = info.get("gpu_id", 0)

        self._user: str = info.get("user").name_cn

        self._create_timestamp: int = round(info.get("start_time", 0.0))
        self._finish_timestamp: int = self._get_finish_timestamp(info)
        self._running_time_in_seconds: int = round(
            info.get("_running_time_in_seconds", 0.0)
        )
        self._gpu_mem_usage_max: str = info.get("task_gpu_memory_max_human", "0MiB")

        self._task_state: str = (
            new_state if new_state is not None else info.get("_state", TaskState.NEWBORN)
        )

        self._is_debug: bool = info.get("is_debug", True)
        self._is_multi_gpu: bool = info.get("is_multi_gpu", False)
        self._conda_env: str = info.get("conda_env", "Unknown")

        self._screen_session_name: str = info.get("screen_session_name", "None")
        self._project_name: str = info.get("project_name", "Unknown")
        self._python_file: str = info.get("python_file", "Unknown")

    @staticmethod
    def _get_finish_timestamp(info: Dict[str, any]) -> int:
        try:
            return round(info.get("finish_time", 0.0))
        except (TypeError, ValueError):
            return 0

    @property
    def task_idx(self) -> str:
        return self._task_idx

    @property
    def pid(self) -> int:
        return self._pid

    @property
    def gpu_id(self) -> int:
        return self._gpu_id

    @property
    def user(self) -> str:
        return self._user

    @property
    def create_timestamp(self) -> int:
        return self._create_timestamp

    @property
    def finish_timestamp(self) -> int:
        return self._finish_timestamp

    @property
    def running_time_in_seconds(self) -> int:
        return self._running_time_in_seconds

    @property
    def gpu_mem_usage_max(self) -> str:
        return self._gpu_mem_usage_max

    @property
    def task_state(self) -> str:
        return self._task_state

    @task_state.setter
    def task_state(self, state: str) -> None:
        self._task_state = state

    @property
    def is_debug(self) -> bool:
        return self._is_debug

    @property
    def is_multi_gpu(self) -> bool:
        return self._is_multi_gpu

    @property
    def conda_env(self) -> str:
        return self._conda_env

    @property
    def screen_session_name(self) -> str:
        return self._screen_session_name

    @property
    def project_name(self) -> str:
        return self._project_name

    @property
    def python_file(self) -> str:
        return self._python_file
