# -*- coding: utf-8 -*-

import sys
import time

from config.settings import (
    GPU_MONITOR_SAMPLING_INTERVAL,
    NUM_GPU,
    WEBHOOK_SEND_LAUNCH_MESSAGE,
)
from feature.group_center import group_center_message
from feature.monitor.gpu.gpu import GPU
from feature.monitor.monitor import Monitor
from feature.monitor.monitor_enum import AllWebhookName, MsgType
from feature.notify.send_msg import handle_normal_text
from feature.notify.webhook import Webhook
from feature.sql.sqlite import get_sql
from feature.global_variable.gpu import (
    global_gpu_info,
    global_gpu_task,
    global_gpu_usage,
)
from feature.utils.logs import get_logger

logger = get_logger()
sql = get_sql()


class NvidiaMonitor(Monitor):
    def __init__(self, num_gpu: int):
        super().__init__("GPU")
        self.num_gpu = num_gpu
        self.is_multi_gpu_machine: bool = num_gpu > 1
        self.monitor_launch_flag = True
        self.total_num_task = 0

        self.gpu_obj_dict: dict[int, GPU] = self.get_gpu_obj()

        from feature.monitor.gpu.gpu_process import GPUProcessInfo

        self.all_processes: dict[int, GPUProcessInfo] = {}

    def get_gpu_obj(self) -> dict[int, GPU]:
        gpu_dict = {}
        for idx in range(NUM_GPU):
            gpu_dict[idx] = GPU(idx, self.is_multi_gpu_machine)

        return gpu_dict

    def gpu_monitor_thread(self):
        while self.monitor_thread_work:
            self.total_num_task = 0
            for idx, gpu in self.gpu_obj_dict.items():
                gpu.update()
                self.total_num_task += gpu.num_task
                self.all_processes.update(gpu.processes)

                # Get gpu status info for webhook msg
                if sys.gettrace() or not self.monitor_launch_flag:
                    continue

                # Send to Group Center
                group_center_message.gpu_monitor_start(idx)
                sql.check_finish_task(gpu.processes, idx)

            self.all_processes.clear()

            if self.should_send_monitor_launch_msg:
                self.send_gpu_monitor_launch_msg()

            time.sleep(GPU_MONITOR_SAMPLING_INTERVAL)

    @property
    def should_send_monitor_launch_msg(self):
        if not self.monitor_launch_flag:
            return False
        else:
            self.monitor_launch_flag = False
        return WEBHOOK_SEND_LAUNCH_MESSAGE and self.total_num_task > 0

    def send_gpu_monitor_launch_msg(self):
        launch_msg_text = []

        for gpu in self.gpu_obj_dict.values():
            gpu.get_all_tasks_msg_body()
            launch_msg_text.append(
                "\n"
                + gpu.gpu_tasks_num_msg_header
                + gpu.all_tasks_msg_body
                + gpu.gpu_status_msg
            )

        if len(launch_msg_text) > 0:
            msg = handle_normal_text("GPU监控启动" + "".join(launch_msg_text))
            Webhook.enqueue_msg_to_webhook(
                msg, MsgType.NORMAL, enable_webhook_name=AllWebhookName.ALL
            )


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

    global_gpu_info.extend(default_gpu_info_dict.copy() for _ in range(NUM_GPU))
    global_gpu_usage.extend(default_gpu_usage_dict.copy() for _ in range(NUM_GPU))
    global_gpu_task.extend([].copy() for _ in range(NUM_GPU))


def start_gpu_monitor_all():
    init_global_gpu_var()
    nvidia_monitor = NvidiaMonitor(NUM_GPU)
    nvidia_monitor.start_monitor(nvidia_monitor.gpu_monitor_thread)


if __name__ == "__main__":
    start_gpu_monitor_all()
