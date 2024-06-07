# -*- coding: utf-8 -*-

import threading
import time
from typing import Dict, Optional

import psutil

from config.settings import (
    CPU_HIGH_TEMPERATURE_THRESHOLD,
    NUM_CPU,
    TEMPERATURE_MONITOR_SAMPLING_INTERVAL,
)
from global_variable.global_system import global_system_info
from monitor.hardware_resource.resource_monitor import Memory
from notify.send_task_msg import (
    send_cpu_except_warning_msg,
    send_cpu_temperature_warning_msg,
)
from utils.converter import convert_bytes_to_mb
from utils.logs import get_logger

logger = get_logger()


class CpuUtils:
    @staticmethod
    def get_cpu_physics_num():
        return psutil.cpu_count(logical=False)

    @staticmethod
    def get_cpu_logic_num():
        return psutil.cpu_count(logical=True)

    @staticmethod
    def get_cpu_percent(interval=0):
        if interval == 0:
            return psutil.cpu_percent()
        return psutil.cpu_percent(interval=interval)



class CPUMonitor:
    def __init__(self, cpu_id: int):
        self.cpu_id: int = cpu_id
        self.high_temperature_trigger: bool = False
        self.thread = None

        self._temperature: float = 0.0

    monitor_thread_work = False

    def start_monitor(self):
        def cpu_monitor_thread():
            logger.info(f"CPU {self.cpu_id} monitor start")
            while monitor_thread_work:
                self.temperature = get_cpu_temperature(self.cpu_id)

                if self.high_temperature_trigger:
                    send_cpu_temperature_warning_msg(self.cpu_id, self.temperature)

                memory_physic = Memory.get_memory_info()
                memory_swap = Memory.get_swap_memory_info()

                global_system_info["memoryPhysicTotalMb"] = convert_bytes_to_mb(memory_physic.total)
                global_system_info["memoryPhysicUsedMb"] = convert_bytes_to_mb(memory_physic.used)
                # global_system_info["memory_physic_free_mb"] = convert_bytes_to_gb(memory_physic.free)

                global_system_info["memorySwapTotalMb"] = convert_bytes_to_mb(memory_swap.total)
                global_system_info["memorySwapUsedMb"] = convert_bytes_to_mb(memory_swap.used)
                # global_system_info["memory_swap_free_mb"] = convert_bytes_to_gb(memory_swap.free)

                time.sleep(TEMPERATURE_MONITOR_SAMPLING_INTERVAL)

            logger.info(f"CPU {self.cpu_id} monitor stop")

        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=cpu_monitor_thread)
        monitor_thread_work = True
        self.thread.start()
        # self.thread.join()

    @property
    def temperature(self):
        return self._temperature

    @temperature.setter
    def temperature(self, new_temperature):
        self.high_temperature_trigger = \
            new_temperature > CPU_HIGH_TEMPERATURE_THRESHOLD > self._temperature

        self._temperature = new_temperature


def get_cpu_temperature(cpu_id: int) -> float:
    cpu_temperature_info = get_cpu_temperature_info()
    if cpu_temperature_info is not None:
        return cpu_temperature_info[cpu_id]
    else:
        send_cpu_except_warning_msg(cpu_id)
        return -1.0


def get_cpu_temperature_info() -> Optional[Dict]:
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


def start_cpu_monitor_all():
    if NUM_CPU is None:
        logger.error("Cannot get the number of CPU.")
        return

    for idx in range(NUM_CPU):
        cpu_monitor_idx = CPUMonitor(idx)
        cpu_monitor_idx.start_monitor()


if __name__ == "__main__":
    start_cpu_monitor_all()
