# -*- coding: utf-8 -*-

import sys
import time

from config.settings import (
    GPU_MONITOR_SAMPLING_INTERVAL,
    NUM_GPU,
    WEBHOOK_DELAY_SEND_SECONDS,
    WEBHOOK_SEND_LAUNCH_MESSAGE,
)
from feature.group_center import group_center_message
from feature.monitor.gpu.gpu import GPU
from feature.monitor.gpu.gpu_process import GPUProcessInfo
from feature.monitor.monitor import Monitor
from feature.notify.send_task_msg import handle_normal_text
from feature.sql.sqlite import get_sql
from global_variable.global_gpu import (
    global_gpu_info,
    global_gpu_task,
    global_gpu_usage,
)
from utils.logs import get_logger

logger = get_logger()
sql = get_sql()


class NvidiaMonitor(Monitor):
    def __init__(self, num_gpu: int):
        self.num_gpu = num_gpu
        self.is_multi_gpu_mechine: bool = num_gpu > 1

        self.gpu_obj_dict: dict[int, GPU] = self.get_gpu_obj()
        self.all_processes: dict[int, GPUProcessInfo] = {}

        self.monitor_name = "GPU"
        self._init_thread_()

    def get_gpu_obj(self) -> dict[int, GPU]:
        gpu_dict = {}
        for idx in range(NUM_GPU):
            gpu_dict[idx] = GPU(idx, self.is_multi_gpu_mechine)

        return gpu_dict

    def gpu_monitor_thread(self):
        monitor_start_flag = True
        while self.monitor_thread_work:
            total_num_task = 0
            for idx, gpu in self.gpu_obj_dict.items():
                gpu.update()
                total_num_task += gpu.num_task

                # Get gpu staus info for webhook msg
                if sys.gettrace() or not monitor_start_flag:
                    continue

                # Send to Group Center
                group_center_message.gpu_monitor_start(idx)
                sql.check_finish_task(gpu.processes, idx)
                self.all_processes.update(gpu.processes)

            if monitor_start_flag and WEBHOOK_SEND_LAUNCH_MESSAGE:
                # Send by WebHook
                self.send_gpu_monitor_start_msg_new()
                monitor_start_flag = False

            time.sleep(GPU_MONITOR_SAMPLING_INTERVAL)

    def send_gpu_monitor_start_msg_new(self):
        """
        启动GPU监控函数
        :param all_gpu_process_info: 所有进程信息字典
        """

        send_start_info = True

        launch_msg_text = []
        cur_gpu_idx = 0

        for process in self.all_processes.values():
            if (
                process.running_time_in_seconds < WEBHOOK_DELAY_SEND_SECONDS
                or process.is_debug
            ):
                send_start_info = False
                continue

            # if process.is_multi_gpu and process.local_rank != 0:
            #     continue

            if cur_gpu_idx != process.gpu_id:
                continue
            launch_msg_text.append(
                process.gpu.gpu_tasks_num_msg_header
                + "".join(process.gpu.all_tasks_msg.values())
                + "\n"
                + process.gpu.gpu_status_msg
            )

            cur_gpu_idx += 1

        if send_start_info:
            handle_normal_text("GPU监控启动\n" + "".join(launch_msg_text))


def init_global_gpu_var():
    default_gpu_info_dict = {
        "gpuName": "NVIDIA GeForce RTX",
        "gpuTDP": "0W",
    }
    default_gpu_usage_dict = {
        "coreUsage": "0",
        "memoryUsage": "0",
        "gpuMemoryUsage": "0GiB",
        "gpuMemoryTotal": "0GiB",
        "gpuPowerUsage": "0",
        "gpuTemperature": "0",
    }
    global_gpu_info.extend([default_gpu_info_dict for _ in range(NUM_GPU)])
    global_gpu_usage.extend([default_gpu_usage_dict for _ in range(NUM_GPU)])
    global_gpu_task.extend([[] for _ in range(NUM_GPU)])


def start_gpu_monitor_all():
    init_global_gpu_var()
    nvidia_monitor = NvidiaMonitor(NUM_GPU)
    nvidia_monitor.start_monitor(nvidia_monitor.gpu_monitor_thread)


if __name__ == "__main__":
    start_gpu_monitor_all()
