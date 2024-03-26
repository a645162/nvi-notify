import copy
import threading
import time
from typing import Dict, List, Optional

from nvitop import Device

from config.config import get_emoji, gpu_monitor_sleep_time, delay_send_seconds
from monitor.GPU.python_process import PythonGPUProcess
from webhook.send_task_msg import (
    send_process_except_warning_msg,
    start_gpu_monitor,
)

from global_variable.global_gpu import (
    global_gpu_info,
    global_gpu_usage,
    global_gpu_task,
)

num_gpu = Device.count()


class NvidiaMonitor:
    def __init__(self, gpu_id: int):
        self.gpu_id = gpu_id
        self.thread: Optional[threading.Thread] = None
        self.processes = {}
        self.nvidia_i: Optional[Device] = None
        self.update_device()
        self.update_gpu_info()
        self.update_gpu_status()

    def update_gpu_info(self):
        cur_gpu_info = {
            "gpuName": self.get_gpu_name(),
            "gpuTDP": self.get_gpu_tdp(),
        }

        global_gpu_info[self.gpu_id].update(cur_gpu_info)

    def update_device(self):
        self.nvidia_i = Device(self.gpu_id)

    def update_gpu_status(self):
        cur_gpu_status = {
            "gpu_usage": self.get_gpu_utl(),

            "gpu_mem_usage": self.get_gpu_mem_usage(),
            "gpu_mem_free": self.get_gpu_mem_free(),
            "gpu_mem_total": self.get_gpu_mem_total(),
            "gpu_mem_percent": self.get_gpu_mem_percent(),

            "gpuPowerUsage": self.get_gpu_power_usage(),
            "gpuTemperature": self.get_gpu_temperature(),
        }

        global_gpu_usage[self.gpu_id]["coreUsage"] = cur_gpu_status["gpu_usage"]
        global_gpu_usage[self.gpu_id]["memoryUsage"] = cur_gpu_status["gpu_mem_percent"]

        global_gpu_usage[self.gpu_id]["gpuMemoryUsage"] = cur_gpu_status["gpu_mem_usage"]
        global_gpu_usage[self.gpu_id]["gpuMemoryTotal"] = cur_gpu_status["gpu_mem_total"]

        global_gpu_usage[self.gpu_id]["gpuPowerUsage"] = cur_gpu_status["gpuPowerUsage"]
        global_gpu_usage[self.gpu_id]["gpuTemperature"] = cur_gpu_status["gpuTemperature"]

        return cur_gpu_status

    def get_gpu_all_processes(self):
        try:
            return self.nvidia_i.processes()
        except:
            send_process_except_warning_msg()

    def get_gpu_name(self) -> str:
        return self.nvidia_i.name()

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

    def get_gpu_power_usage(self) -> int:
        return int(round(self.nvidia_i.power_usage() / 1000, 0))

    def get_gpu_tdp(self) -> int:
        return int(round(self.nvidia_i.power_limit() / 1000, 0))

    def get_gpu_temperature(self) -> int:
        return self.nvidia_i.temperature()

    def get_all_tasks_msg(self, process_info: Dict) -> Dict:
        all_tasks_msg_dict = {}
        for idx, info in enumerate(process_info.values()):
            task_msg = (
                f"{get_emoji(idx)}{'🐞' if info.is_debug else ''}"
                f"用户: {info.user['name']}  "
                f"显存占用: {info.taks_gpu_memory_human}  "
                f"运行时长: {info.running_time_human}\n"
            )
            all_tasks_msg_dict.update({info.pid: task_msg})

        return all_tasks_msg_dict

    monitor_thread_work = False

    def start_monitor(self):
        def gpu_monitor_thread():
            print(f"GPU {self.gpu_id} monitor start")
            monitor_start_flag = True
            while monitor_thread_work:
                # GPU线程周期开始

                # Update Gpu Status
                self.update_gpu_status()

                # update all process info
                for pid in self.processes:
                    self.processes[pid].gpu_status = self.update_gpu_status()
                    self.processes[pid].update_cmd()
                    self.processes[pid].update_gpu_process_info()

                # check death process pid
                tmp_process = copy.copy(self.processes)
                cur_gpu_all_processes = self.get_gpu_all_processes()
                for pid in tmp_process:
                    if pid not in cur_gpu_all_processes:
                        del self.processes[pid].gpu_all_tasks_msg[pid]
                        self.processes[pid].state = "death"
                        del self.processes[pid]

                # update new process
                for pid, gpu_process in self.get_gpu_all_processes().items():
                    if pid not in self.processes:
                        new_process = PythonGPUProcess(pid, self.gpu_id, gpu_process)
                        if new_process.is_python:
                            if new_process.running_time_in_seconds > delay_send_seconds:
                                new_process.state = "working"
                            else:
                                new_process.state = "newborn"
                            new_process.gpu_status = self.update_gpu_status()
                            self.processes[pid] = new_process
                        else:
                            continue

                # get gpu staus info for webhook msg 
                all_tasks_msg_dict = self.get_all_tasks_msg(self.processes)
                for pid in self.processes:
                    self.processes[pid].gpu_all_tasks_msg = all_tasks_msg_dict
                    self.processes[pid].num_task = len(self.processes)

                if monitor_start_flag and len(self.processes) > 0:
                    start_gpu_monitor(self.gpu_id, self.processes)
                    monitor_start_flag = False

                # 在监视线程中就进行处理，哪怕这里阻塞了，也就是相当于多加一点延时
                current_gpu_list: List = list(self.processes.values()).copy()
                current_gpu_list.sort(key=lambda x: x.pid)

                global_gpu_task[self.gpu_id].clear()
                global_gpu_task[self.gpu_id].extend(current_gpu_list)

                time.sleep(gpu_monitor_sleep_time)
                # 线程周期结束

            print(f"GPU {self.gpu_id} monitor stop")

        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=gpu_monitor_thread)
        monitor_thread_work = True
        self.thread.start()

    def stop_monitor(self):
        monitor_thread_work = False
        if self.thread is not None and self.thread.is_alive():
            self.thread.join()


def start_gpu_monitor_all():
    for idx in range(num_gpu):
        # Initialize global variables
        global_gpu_info.append(
            {
                "gpuName": "NVIDIA GeForce RTX",

                "gpuTDP": "0W",
            }
        )
        global_gpu_usage.append(
            {
                "coreUsage": "0",
                "memoryUsage": "0",

                "gpuMemoryUsage": "0GiB",
                "gpuMemoryTotal": "0GiB",

                "gpuPowerUsage": "0",

                "gpuTemperature": "0",
            }
        )
        global_gpu_task.append([])

        nvidia_monitor_idx = NvidiaMonitor(idx)
        # print(NvidiaMonitor_i.get_gpu_usage())
        nvidia_monitor_idx.start_monitor()


if __name__ == "__main__":
    start_gpu_monitor_all()
