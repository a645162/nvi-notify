import threading
import time
from typing import Dict

from nvitop import *

from config import config
from monitor.process import PythonProcess
from monitor.send_task_info import start_gpu_monitor
from webhook import wework

sleep_time = config.gpu_monitor_sleep_time
num_gpu = Device.count()

class NvidiaMonitor:
    def __init__(self, gpu_id: int):
        self.gpu_id = gpu_id
        self.thread = None
        self.processes = {}
        self.nvidia_i = None
        self.update_device()

    def update_device(self):
        self.nvidia_i = Device(self.gpu_id)

    def update_gpu_status(self):
        cur_gpu_status = {
            "gpu_usage": self.get_gpu_utl(),
            "gpu_mem_usage": self.get_gpu_mem_usage(),
            "gpu_mem_free": self.get_gpu_mem_free(),
            "gpu_mem_percent": self.get_gpu_mem_percent(),
            "gpu_mem_total": self.get_gpu_mem_total(),
        }

        return cur_gpu_status

    def get_gpu_all_processes(self):
        try:
            return self.nvidia_i.processes()
        except:
            wework.send_process_except_msg()

    def get_gpu_utl(self):
        return self.nvidia_i.gpu_utilization()

    def get_gpu_mem_utl(self):
        return self.nvidia_i.memory_utilization()

    def get_gpu_mem_usage(self):
        return self.nvidia_i.memory_used_human()

    def get_gpu_mem_free(self):
        return self.nvidia_i.memory_free_human()

    def get_gpu_mem_percent(self):
        return self.nvidia_i.memory_percent()

    def get_gpu_mem_total(self):
        return self.nvidia_i.memory_total_human()

    def get_all_tasks_msg(self, process_info: Dict) -> str:
        all_tasks_msg = []
        for idx, info in enumerate(process_info.values()):
            debug_info = "🐞" if info.is_debug is not None else ""

            task_msg = (
                f"{config.get_emoji(idx)}{debug_info}"
                f"用户: {info.user['name']}  "
                f"显存占用: {info.memory_usage}  "
                f"运行时长: {info.running_time_human}\n"
            )
            all_tasks_msg.append(task_msg)

        self.all_tasks_msg = "".join(all_tasks_msg)

    monitor_thread_work = False

    def start_monitor(self):
        def monitor_thread():
            print(f"GPU {self.gpu_id} monitor start")
            monitor_start_flag = True

            while monitor_thread_work:
                self.get_all_tasks_msg(self.processes)
                for pid in self.processes.keys():
                    if self.processes[pid].state == 0:
                        del self.processes[pid]
                        continue

                    self.processes[pid].update_cmd()
                    self.processes[pid].update_gpu_process_info()
                    self.processes[pid].gpu_status = self.update_gpu_status()
                    self.processes[pid].gpu_all_tasks_msg = self.all_tasks_msg
                    self.processes[pid].num_task = len(self.get_gpu_all_processes())

                for pid, gpu_process in self.get_gpu_all_processes().items():
                    if pid not in self.processes:
                        new_process = PythonProcess(pid, self.gpu_id, gpu_process)
                        if new_process.is_python:
                            new_process.state = "newborn"
                            self.processes[pid] = new_process
                        else:
                            continue

                if monitor_start_flag and self.all_tasks_msg != "":
                    start_gpu_monitor(self.gpu_id, self.all_tasks_msg, self.processes)
                    monitor_start_flag = False

                time.sleep(sleep_time)

            print(f"GPU {self.gpu_id} monitor stop")

        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=monitor_thread)
        monitor_thread_work = True
        self.thread.start()
        # self.thread.join()

    def stop_monitor(self):
        monitor_thread_work = False
        if self.thread is not None and self.thread.is_alive():
            self.thread.join()


def start_gpu_monitor_all():

    for idx in range(num_gpu):
        nvidia_monitor_idx = NvidiaMonitor(idx)
        # print(NvidiaMonitor_i.get_gpu_usage())
        nvidia_monitor_idx.start_monitor()


if __name__ == "__main__":
    start_gpu_monitor_all()
