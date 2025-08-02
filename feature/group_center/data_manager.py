from feature.monitor.gpu import gpu_process
from feature.utils import logs

logger = logs.get_logger()


# class PythonGPUProcessRecord:
#     def __init__(self, gpu_process: "gpu_process.GPUProcessInfo"):
#         self.datetime: datetime = datetime.now()
#         self.timestamp: int = int(datetime.timestamp(self.datetime))
#         if self.timestamp > DataManager.record_latest_timestamp:
#             DataManager.record_latest_timestamp = self.timestamp

#         self.gpu_process: "gpu_process.GPUProcessInfo" = gpu_process


class DataManager:
    def __init__(self) -> None:
        logger.info("Global Variable Initializing...")

        self.disk_info_response_dict: dict[str, dict] = {}
        self.disk_info_user_response_dict: dict[str, dict] = {}

        self.gpu_info: list[dict] = []
        self.gpu_usage: list[dict] = []
        self.gpu_task: list[list[gpu_process.GPUProcessInfo]] = []

        self.system_info: dict = {}

        # self.record_latest_timestamp: int = 0
        # self.task_new_born: list[PythonGPUProcessRecord] = []
        # self.task_history: list[PythonGPUProcessRecord] = []

    def get_gpu_count(self) -> int:
        if len(self.gpu_usage) != len(self.gpu_task):
            raise ValueError("gpu_usage and gpu_task should have the same length.")
        return len(self.gpu_task)

    def gpu_updated(self) -> None:
        pass


def get_data_manager() -> DataManager:
    return data_manager


data_manager = DataManager()
