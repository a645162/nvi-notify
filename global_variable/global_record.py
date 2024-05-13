from typing import List
import datetime

from monitor.GPU.python_process import PythonGPUProcess


class PythonGPUProcessRecord:

    def __init__(self, gpu_process: PythonGPUProcess):
        self.datetime: datetime.datetime = datetime.datetime.now()
        self.timestamp: int = int(datetime.datetime.timestamp(self.datetime))

        self.gpu_process: PythonGPUProcess = gpu_process


task_new_born: List[PythonGPUProcessRecord] = []
task_history: List[PythonGPUProcessRecord] = []
