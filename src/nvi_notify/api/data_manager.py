from dataclasses import dataclass, field

from nvi_notify.entity import process
from nvi_notify.utils import logs

logger = logs.get_logger()


# class PythonGPUProcessRecord:
#     def __init__(self, gpu_process: "gpu_process.GPUProcessInfo"):
#         self.datetime: datetime = datetime.now()
#         self.timestamp: int = int(datetime.timestamp(self.datetime))
#         if self.timestamp > DataManager.record_latest_timestamp:
#             DataManager.record_latest_timestamp = self.timestamp

#         self.gpu_process: "gpu_process.GPUProcessInfo" = gpu_process


@dataclass
class GlobalResponses:
    disk_info_response_dict: dict[str, dict] = field(default_factory=dict)
    disk_info_user_response_dict: dict[str, dict] = field(default_factory=dict)
    gpu_info: list[dict] = field(default_factory=list)
    gpu_usage: list[dict] = field(default_factory=list)
    gpu_task: list[list[process.GPUProcessInfo]] = field(default_factory=list)
    system_info: dict = field(default_factory=dict)
    # record_latest_timestamp: int = field(default=0)
    # task_new_born: list[process.GPUProcessInfo] = field(default_factory=list)
    # task_history: list[process.GPUProcessInfo] = field(default_factory=list)

    def __post_init__(self) -> None:
        logger.info("Global Variable Initializing...")

    def get_gpu_count(self) -> int:
        if len(self.gpu_usage) != len(self.gpu_task):
            raise ValueError("gpu_usage and gpu_task should have the same length.")
        return len(self.gpu_task)

    def gpu_updated(self) -> None:
        pass


def get_data_manager() -> GlobalResponses:
    return data_manager


data_manager = GlobalResponses()
