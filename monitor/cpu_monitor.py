import subprocess
import threading
import time
from typing import Dict

import psutil

from config import config
from monitor.send_task_info import (
    send_cpu_except_warning_msg,
    send_cpu_temperature_warning_msg,
)

sleep_time = config.gpu_monitor_sleep_time
HIGH_TEMPERATURE_THRESHOLD = 70


class CPUMonitor:
    def __init__(self, cpu_id: int):
        self.cpu_id: int = cpu_id
        self.high_temperature_trigger: bool = False
        self.thread = None

        self._temperature: float = 0.0

    monitor_thread_work = False

    def start_monitor(self):
        def monitor_thread():
            print(f"CPU {self.cpu_id} monitor start")
            while monitor_thread_work:
                self.temperature = get_cpu_temperature(self.cpu_id)

                if self.high_temperature_trigger:
                    send_cpu_temperature_warning_msg(self.cpu_id, self.temperature)

                time.sleep(sleep_time)

            print(f"CPU {self.cpu_id} monitor stop")

        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=monitor_thread)
        monitor_thread_work = True
        self.thread.start()
        # self.thread.join()

    @property
    def temperature(self):
        return self._temperature

    @temperature.setter
    def temperature(self, new_temperature):
        self.high_temperature_trigger = (
            new_temperature > HIGH_TEMPERATURE_THRESHOLD
            and self._temperature < HIGH_TEMPERATURE_THRESHOLD
        )

        self._temperature = new_temperature


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
