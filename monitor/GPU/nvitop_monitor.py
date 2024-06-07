# -*- coding: utf-8 -*-

import copy
import threading
import time
from typing import Dict, List, Optional

from nvitop import Device

from config.settings import (
    GPU_MONITOR_SAMPLING_INTERVAL,
    NUM_GPU,
    WEBHOOK_DELAY_SEND_SECONDS,
    GPU_MONITOR_AUTO_RESTART,
    get_emoji,
)
from global_variable.global_gpu import (
    global_gpu_info,
    global_gpu_task,
    global_gpu_usage,
)
from monitor.GPU.info import GPU_INFO, gpu_name_filter
from monitor.GPU.gpu_process import GPUProcessInfo
from utils.converter import convert_bytes_to_mb
from utils.sqlite import get_sql

from group_center import group_center

from notify.send_task_msg import (
    send_process_except_warning_msg,
    send_gpu_monitor_start_msg,
)

from utils.logs import get_logger

logger = get_logger()
sql = get_sql()


class NvidiaMonitor:
    def __init__(self, gpu_id: int):
        self.gpu_id = gpu_id
        self.thread: Optional[threading.Thread] = None
        self.processes: dict = {}
        self.nvidia_i: Optional[Device] = None
        self.get_device()
        self.get_gpu_info()
        self.update_gpu_status()

    def get_gpu_info(self):
        cur_gpu_info = {
            "gpuName": self.get_gpu_name_short(),
            "gpuTDP": self.get_gpu_tdp(),
        }

        global_gpu_info[self.gpu_id].update(cur_gpu_info)

    def get_device(self):
        self.nvidia_i = Device(self.gpu_id)

    def update_gpu_status(self) -> GPU_INFO:
        gpu_status = GPU_INFO(
            {
                # GPU Percent
                "gpu_usage": self.get_gpu_utl(),
                "gpu_mem_percent": self.get_gpu_mem_percent(),
                # GPU Memory Bytes
                "gpu_mem_total_bytes": self.get_gpu_mem_total_bytes(),
                # GPU Memory Human(String)
                "gpu_mem_usage": self.get_gpu_mem_usage(),
                "gpu_mem_free": self.get_gpu_mem_free(),
                "gpu_mem_total": self.get_gpu_mem_total(),
                # Power(Int)
                "gpu_power_usage": self.get_gpu_power_usage(),
                "gpu_temperature": self.get_gpu_temperature(),
            }
        )

        global_gpu_usage[self.gpu_id]["coreUsage"] = gpu_status.utl
        global_gpu_usage[self.gpu_id]["memoryUsage"] = gpu_status.mem_percent

        global_gpu_usage[self.gpu_id]["gpuMemoryTotalMB"] = convert_bytes_to_mb(
            gpu_status.mem_total_bytes
        )

        global_gpu_usage[self.gpu_id]["gpuMemoryUsage"] = gpu_status.mem_usage
        global_gpu_usage[self.gpu_id]["gpuMemoryTotal"] = gpu_status.mem_total

        global_gpu_usage[self.gpu_id]["gpuPowerUsage"] = gpu_status.power_usage
        global_gpu_usage[self.gpu_id]["gpuTemperature"] = gpu_status.temperature

        return gpu_status

    def get_gpu_all_processes(self):
        try:
            return self.nvidia_i.processes()
        except Exception as e:
            logger.error(e)
            send_process_except_warning_msg()

    def get_gpu_name(self) -> str:
        return self.nvidia_i.name()

    def get_gpu_name_short(self) -> str:
        return gpu_name_filter(self.get_gpu_name())

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

    def get_gpu_mem_total_bytes(self):
        return self.nvidia_i.memory_total()

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
        for idx, process in enumerate(process_info.values()):
            idx_emoji = get_emoji(idx)
            debug_emoji = "🐞" if process.is_debug else ""
            task_msg = (
                f"{idx_emoji}{debug_emoji}"
                f"用户: {process.user['name']}  "
                f"最大显存: {process.task_gpu_memory_max_human}  "
                f"运行时长: {process.running_time_human}\n"
            )
            all_tasks_msg_dict.update({process.pid: task_msg})

        return all_tasks_msg_dict

    monitor_thread_work: bool = False

    def start_monitor(self):
        def gpu_monitor_thread():
            logger.info(f"GPU {self.gpu_id} monitor start")
            monitor_start_flag = True
            while self.monitor_thread_work:
                # GPU线程周期开始

                # Update Gpu Status
                self.update_gpu_status()

                # update all process info
                for pid in self.processes:
                    self.processes[pid].gpu_status = self.update_gpu_status()
                    self.processes[pid].update_gpu_process_info()
                    if self.processes[pid].state == "newborn":
                        self.processes[pid].update_cmd()

                # check death process pid
                tmp_process = copy.copy(self.processes)
                cur_gpu_all_processes = self.get_gpu_all_processes()
                for pid in tmp_process:
                    if pid not in cur_gpu_all_processes:
                        del self.processes[pid].gpu_all_tasks_msg[pid]
                        self.processes[pid].set_finish_time()
                        self.processes[pid].state = "death"
                        del self.processes[pid]
                del tmp_process

                # update new process
                for pid, gpu_process in self.get_gpu_all_processes().items():
                    if pid not in self.processes:
                        new_process = GPUProcessInfo(pid, self.gpu_id, gpu_process)
                        if new_process.is_python:
                            if (
                                    new_process.running_time_in_seconds
                                    > WEBHOOK_DELAY_SEND_SECONDS
                            ):
                                new_process.state = "working"
                            else:
                                new_process.state = "newborn"
                            new_process.gpu_status = self.update_gpu_status()
                            self.processes[pid] = new_process
                        else:
                            continue

                # Get gpu staus info for webhook msg
                all_tasks_msg_dict = self.get_all_tasks_msg(self.processes)
                for pid in self.processes:
                    self.processes[pid].gpu_all_tasks_msg = all_tasks_msg_dict
                    self.processes[pid].num_task = len(self.processes)

                if monitor_start_flag and len(self.processes) > 0:
                    # Send to Group Center
                    group_center.gpu_monitor_start()

                    # Send by WebHook
                    send_gpu_monitor_start_msg(self.gpu_id, self.processes)

                    sql.check_finish_task(self.processes, self.gpu_id)
                    monitor_start_flag = False

                # 在监视线程中就进行处理，哪怕这里阻塞了，也就是相当于多加一点延时
                current_gpu_list: List = list(self.processes.values()).copy()
                current_gpu_list.sort(key=lambda x: x.pid)

                global_gpu_task[self.gpu_id].clear()
                global_gpu_task[self.gpu_id].extend(current_gpu_list)

                time.sleep(GPU_MONITOR_SAMPLING_INTERVAL)
                # 线程周期结束

            logger.info(f"GPU {self.gpu_id} monitor stop")

        def thread_worker():
            restart_times = 0

            while self.monitor_thread_work:
                if restart_times > 0:
                    logger.debug(
                        f"GPU {self.gpu_id} monitor restart times: {restart_times}"
                    )

                if GPU_MONITOR_AUTO_RESTART:
                    # 需要重启不可以报错导致线程崩溃
                    try:
                        gpu_monitor_thread()
                    except Exception as e:
                        logger.error(f"GPU {self.gpu_id} monitor error: {e}")
                        time.sleep(60)
                else:
                    # 不需要重启就正常报错
                    gpu_monitor_thread()
                    break
                restart_times += 1

        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=thread_worker)
        self.monitor_thread_work = True
        self.thread.start()

    def stop_monitor(self):
        self.monitor_thread_work = False
        if self.thread is not None and self.thread.is_alive():
            self.thread.join()


def start_gpu_monitor_all():
    for idx in range(NUM_GPU):
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
        nvidia_monitor_idx.start_monitor()
        time.sleep(0.5)  # waiting


if __name__ == "__main__":
    start_gpu_monitor_all()
