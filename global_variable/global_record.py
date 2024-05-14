from typing import List
import datetime

from monitor.GPU.python_process import PythonGPUProcess

record_latest_timestamp: int = 0


class PythonGPUProcessRecord:

    def __init__(self, gpu_process: PythonGPUProcess):
        self.datetime: datetime.datetime = datetime.datetime.now()
        self.timestamp: int = int(datetime.datetime.timestamp(self.datetime))

        global record_latest_timestamp
        if self.timestamp > record_latest_timestamp:
            record_latest_timestamp = self.timestamp

        self.gpu_process: PythonGPUProcess = gpu_process


task_new_born: List[PythonGPUProcessRecord] = []
task_history: List[PythonGPUProcessRecord] = []
