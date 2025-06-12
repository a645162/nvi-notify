from datetime import datetime

from feature.monitor.gpu.gpu_process import GPUProcessInfo
from feature.utils.logs import get_logger

logger = get_logger()


# class PythonGPUProcessRecord:
#     def __init__(self, gpu_process: GPUProcessInfo):
#         self.datetime: datetime = datetime.now()
#         self.timestamp: int = int(datetime.timestamp(self.datetime))
#         if self.timestamp > DataManager.record_latest_timestamp:
#             DataManager.record_latest_timestamp = self.timestamp

#         self.gpu_process: GPUProcessInfo = gpu_process


class DataManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(DataManager, cls).__new__(cls, *args, **kwargs)
            cls._initialize_variables()
        return cls._instance

    @classmethod
    def _initialize_variables(cls):
        logger.info("Global Variable Initializing...")

        cls.disk_info_response_dict: dict[str, dict] = {}
        cls.disk_info_user_response_dict: dict[str, dict] = {}

        cls.gpu_info: list[dict] = []
        cls.gpu_usage: list[dict] = []
        cls.gpu_task: list[list[GPUProcessInfo]] = []

        cls.system_info: dict = {}

        # cls.record_latest_timestamp: int = 0
        # cls.task_new_born: list[PythonGPUProcessRecord] = []
        # cls.task_history: list[PythonGPUProcessRecord] = []

    @classmethod
    def get_gpu_count(cls):
        if len(cls.gpu_usage) != len(cls.gpu_task):
            raise ValueError(
                "gpu_usage and gpu_task should have the same length."
            )
        return len(cls.gpu_task)

    @classmethod
    def gpu_updated(cls):
        pass
