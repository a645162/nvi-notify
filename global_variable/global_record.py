import datetime
from typing import List

from monitor.GPU.gpu_process import GPUProcessInfo

record_latest_timestamp: int = 0


class PythonGPUProcessRecord:

    def __init__(self, gpu_process: GPUProcessInfo):
        self.datetime: datetime.datetime = datetime.datetime.now()
        self.timestamp: int = int(datetime.datetime.timestamp(self.datetime))

        global record_latest_timestamp
        if self.timestamp > record_latest_timestamp:
            record_latest_timestamp = self.timestamp

        self.gpu_process: GPUProcessInfo = gpu_process


task_new_born: List[PythonGPUProcessRecord] = []
task_history: List[PythonGPUProcessRecord] = []
