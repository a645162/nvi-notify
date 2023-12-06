from nvitop import *
import threading
import time

from utils import my_time
from webhook import wework

threshold = 20
sleep_time = 5


def send_text_to_wework(gpu_id: int, msg: str):
    now_time = my_time.get_now_time()
    send_text = \
        (
            f"GPU Monitor\n"
            f"\tGPU {gpu_id}\n"
            f"\t{msg}\n"
            f"Time: {now_time}"
        )
    wework.send_text(send_text)


def gpu_start_use(gpu_id: int, gpu_usage: int):
    print(f"GPU {gpu_id} start use")
    send_text_to_wework(
        gpu_id,
        f"1 Start Use\n"
        f"\tGPU Usage: {gpu_usage}%"
    )


def gpu_stop_use(gpu_id: int, gpu_usage: int):
    print(f"GPU {gpu_id} stop use")
    send_text_to_wework(
        gpu_id,
        f"0 Stop Use\n"
        f"\tGPU Usage: {gpu_usage}%"
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

    def get_gpu_usage(self):
        return self.nvidia_i.gpu_utilization()

    monitor_thread_work = False

    def start_monitor(self):

        def monitor_thread():

            print(f"GPU {self.gpu_id} monitor start")
            print(f"GPU {self.gpu_id} threshold is {threshold}")

            start_use = False
            last_usage = 0
            while monitor_thread_work:
                gpu_usage = self.get_gpu_usage()

                if abs(gpu_usage - last_usage) >= threshold:
                    if gpu_usage > threshold:
                        if not start_use:
                            print(f"GPU {self.gpu_id} usage is {gpu_usage}%")
                            start_use = True
                            gpu_start_use(self.gpu_id, gpu_usage)
                    else:
                        if start_use:
                            print(f"GPU {self.gpu_id} usage is {gpu_usage}%")
                            start_use = False
                            gpu_stop_use(self.gpu_id, gpu_usage)
                elif gpu_usage >= threshold + 10:
                    if not start_use:
                        print(f"GPU {self.gpu_id} usage is {gpu_usage}%")
                        start_use = True
                        gpu_start_use(self.gpu_id, gpu_usage)
                elif gpu_usage <= 3:
                    if start_use:
                        print(f"GPU {self.gpu_id} usage is {gpu_usage}%")
                        start_use = False
                        gpu_stop_use(self.gpu_id, gpu_usage)

                last_usage = gpu_usage
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


if __name__ == '__main__':

    # Get GPU count
    gpu_count = Device.count()

    for i in range(gpu_count):
        nvidia_monitor_i = nvidia_monitor(i)
        # print(nvidia_monitor_i.get_gpu_usage())
        nvidia_monitor_i.start_monitor()
