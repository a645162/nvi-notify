from nvitop import *
import threading
import time

from utils import my_time
from webhook import wework

from config import config

threshold = config.gpu_monitor_usage_threshold
sleep_time = config.gpu_monitor_sleep_time


def send_text_to_wework(msg: str):
    now_time = my_time.get_now_time()
    send_text = \
        (
            f"GPU Monitor\n"
            f"\t{msg}\n"
            f"Time: {now_time}"
        )
    wework.send_text(send_text)


def gpu_create_task(
        task_info: dict,
        gpu_usage: int,
        gpu_mem_usage: str,
        gpu_mem_free: str,
        gpu_mem_percent: float,
        gpu_mem_total: str
):
    print(f"GPU {task_info['device']} start create new task:{task_info['pid']}")
    if not task_info['debug']:
        send_text_to_wework(
            f"{task_info['device']}Create New Task\n"
            f"\tGPU Usage: {gpu_usage}%\n"
            f"\tGPU Mem: {gpu_mem_usage}/{gpu_mem_total}({gpu_mem_percent}%)\n"
            f"\tGPU Mem Free: {gpu_mem_free}\n"
        )


def gpu_finish_task(
        task_info: dict,
        gpu_usage: int,
        gpu_mem_usage: str,
        gpu_mem_free: str,
        gpu_mem_percent: float,
        gpu_mem_total: str
):
    print(f"GPU {task_info['device']} finish task:{task_info['pid']}")
    if not task_info['debug']:
        send_text_to_wework(
            f"{task_info['device']}Finish Task\n"
            f"\tGPU Usage: {gpu_usage}%\n"
            f"\tGPU Mem: {gpu_mem_usage}/{gpu_mem_total}({gpu_mem_percent}%)\n"
            f"\tGPU Mem Free: {gpu_mem_free}\n"
        )


class nvidia_monitor:
    gpu_id: int

    def __init__(self, gpu_id):
        self.gpu_id = gpu_id
        self.thread = None
        self.nvidia_i = None
        self.update_device()

    def update_device(self):
        self.nvidia_i = Device(self.gpu_id)

    def get_valid_gpu_task(self):
        gpu_task_info = {}
        for pid, gpu_process in self.get_gpu_all_processes().items():
            process_name = gpu_process.name().lower()
            if len(gpu_process.cmdline()) > 1:
                debug_flag = config.ignore_vscode_debug_procees_name in gpu_process.cmdline()[1]
            else:
                debug_flag = False

            if process_name not in config.ignore_procees_name:
                start_time = gpu_process.create_time()

                gpu_task_info[pid] = {
                    "memory_usage": gpu_process.gpu_memory_human(),
                    "device": self.gpu_id,
                    "user": config.user_dict[gpu_process.cwd().split("/")[-1]],
                    "running_time": gpu_process.running_time_human(),
                    "debug": debug_flag,
                }

        return gpu_task_info

    def get_gpu_all_processes(self):
        return self.nvidia_i.processes()

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

    monitor_thread_work = False

    def start_monitor(self):

        def monitor_thread():

            print(f"GPU {self.gpu_id} monitor start")
            print(f"GPU {self.gpu_id} threshold is {threshold}")

            last_runing_task = {}
            while monitor_thread_work:
                runing_task = self.get_valid_gpu_task()

                if runing_task.keys() != last_runing_task.keys():
                    new_task_pid = set(runing_task.keys()) - set(last_runing_task.keys())
                    if new_task_pid:
                        for pid in new_task_pid:
                            gpu_create_task(
                                runing_task[pid],
                                self.get_gpu_utl(),
                                self.get_gpu_mem_usage(),
                                self.get_gpu_mem_free(),
                                self.get_gpu_mem_percent(),
                                self.get_gpu_mem_total()
                            )

                    finished_task_pid = set(last_runing_task.keys()) - set(runing_task.keys())
                    if finished_task_pid:
                        for pid in finished_task_pid:
                            gpu_finish_task(
                                last_runing_task[pid],
                                self.get_gpu_utl(),
                                self.get_gpu_mem_usage(),
                                self.get_gpu_mem_free(),
                                self.get_gpu_mem_percent(),
                                self.get_gpu_mem_total()
                            )

                last_runing_task = runing_task
                time.sleep(sleep_time)

            print(f"GPU {self.gpu_id} monitor stop")

        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=monitor_thread)
        monitor_thread_work = True
        self.thread.start()

    def stop_monitor(self):
        monitor_thread_work = False
        if self.thread is not None and self.thread.is_alive():
            self.thread.join()


def start_monitor_all():
    # Get GPU count
    gpu_count = Device.count()

    for i in range(gpu_count):
        nvidia_monitor_i = nvidia_monitor(i)
        # print(nvidia_monitor_i.get_gpu_usage())
        nvidia_monitor_i.start_monitor()


if __name__ == '__main__':
    start_monitor_all()
