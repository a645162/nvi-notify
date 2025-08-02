from feature.monitor import enum


class TaskInfoForSQL:
    def __init__(self, info: dict, new_state: enum.TaskState | None = None) -> None:
        self.task_idx: str = info.get("task_id", "Unknown")
        self.pid: int = info.get("pid", 0)
        self.gpu_id: int = info.get("gpu_id", 0)

        self.user: str = info.get("user").name_cn  # type: ignore

        self.create_timestamp: int = round(info.get("start_time", 0.0))
        self.finish_timestamp: int = round(info.get("finish_time", 0.0))
        self.running_time_in_seconds: int = round(
            info.get("_running_time_in_seconds", 0.0)
        )
        self.gpu_mem_usage_max: str = info.get("task_gpu_memory_max_human", "0MiB")

        self.task_state: enum.TaskState = (
            new_state
            if new_state is not None
            else info.get("_state", enum.TaskState.NEWBORN)
        )

        self.is_debug: bool = info.get("is_debug", True)
        self.is_multi_gpu: bool = info.get("is_multi_gpu", False)
        self.conda_env: str = info.get("conda_env", "Unknown")

        self.screen_session_name: str = info.get("screen_session_name", "None")
        self.project_name: str = info.get("project_name", "Unknown")
        self.python_file: str = info.get("python_file", "Unknown")
