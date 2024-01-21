import subprocess
import threading
import time
from typing import Dict

import psutil

# from config import config
# from utils import ip, my_time
# from webhook import wework

# local_ip = ip.get_local_ip()
# server_name = config.server_name
# sleep_time = config.gpu_monitor_sleep_time
local_ip = "0.0.0.0"
server_name = "test"
sleep_time = 5


def send_cpu_except_warning_msg(cpu_id: int):
    warning_message = (
        f"⚠️⚠️{server_name}获取CPU:{cpu_id}温度失败！⚠️⚠️\n"
        f"IP: {local_ip}\n"
        # f"⏰{my_time.get_now_time()}"
    )
    # wework.direct_send_text_warning(msg=warning_message)


def send_cpu_temperature_warning_msg(cpu_id: int, cpu_temperature: float):
    warning_message = (
        f"🤒🤒{server_name}的CPU:{cpu_id}温度已经超过{cpu_temperature}°C\n"
        f"IP: {local_ip}\n"
        # f"⏰{my_time.get_now_time()}"
    )
    # wework.direct_send_text_warning(msg=warning_message)


class CPUMonitor:
    def __init__(self, cpu_id: int):
        self.cpu_id = cpu_id
        self.thread = None

    monitor_thread_work = False

    def start_monitor(self):
        def monitor_thread():
            print(f"CPU {self.cpu_id} monitor start")
            last_cpu_temperature = 0
            high_temperature_trigger = False
            while monitor_thread_work:
                now_cpu_temperature = get_cpu_temperature(self.cpu_id)

                if now_cpu_temperature >= 70:
                    if last_cpu_temperature < 70:
                        high_temperature_trigger = True
                    else:
                        high_temperature_trigger = False
                else:
                    high_temperature_trigger = False

                if high_temperature_trigger:
                    send_cpu_temperature_warning_msg(self.cpu_id, now_cpu_temperature)

                time.sleep(sleep_time)
                last_cpu_temperature = now_cpu_temperature

            print(f"CPU {self.cpu_id} monitor stop")

        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=monitor_thread)
        monitor_thread_work = True
        self.thread.start()
        # self.thread.join()


def get_cpu_temperature(cpu_id: int) -> float:
    cpu_temperature_info = get_cpu_temperature_info()
    if cpu_temperature_info is not None:
        return cpu_temperature_info[cpu_id]
    else:
        send_cpu_except_warning_msg(cpu_id)
        return -1.0


def get_cpu_temperature_info() -> Dict:
    if not hasattr(psutil, "sensors_temperatures"):
        return None
    temps = psutil.sensors_temperatures()
    if not temps:
        return None
    cpu_temperature_info = {}
    idx = 0
    for name, entries in temps.items():
        if name == "coretemp":
            for entry in entries:
                if "Package" in entry.label or "Package" in name:
                    cpu_temperature_info.update({idx: entry.current})
                    idx += 1

    return cpu_temperature_info


def get_cpu_physics_num() -> int:
    command = "cat /proc/cpuinfo | grep 'physical id' | sort -u | wc -l"
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, text=True)

    if result.returncode == 0:
        return int(result.stdout.strip())


def start_cpu_monitor_all():
    global num_cpu
    num_cpu = get_cpu_physics_num()

    for idx in range(num_cpu):
        cpu_monitor_idx = CPUMonitor(idx)
        cpu_monitor_idx.start_monitor()


if __name__ == "__main__":
    start_cpu_monitor_all()
