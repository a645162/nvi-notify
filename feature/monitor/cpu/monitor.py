# -*- coding: utf-8 -*-

import time

import psutil
from feature.monitor.cpu.cpu import CPU, CPUInfo

from config.settings import TEMPERATURE_MONITOR_SAMPLING_INTERVAL
from feature.monitor.memory.memory import MemoryInfo
from feature.monitor.monitor import Monitor
from feature.notify.send_msg import (
    send_cpu_except_warning_msg,
    send_cpu_temperature_warning_msg,
)
from utils.logs import get_logger

logger = get_logger()


class CPUMonitor(Monitor):
    def __init__(self, num_cpu: int):
        super().__init__("CPU")
        self.num_cpu: int = num_cpu
        self.cpu_dict: dict[int, CPU] = self.get_cpu_obj()

    def get_cpu_obj(self) -> dict[int, CPU]:
        cpu_dict: dict[int, CPU] = {}
        for idx in range(self.num_cpu):
            cpu_dict[idx] = CPU(idx)

        return cpu_dict

    def cpu_monitor_thread(self):
        while self.monitor_thread_work:
            MemoryInfo.update()

            temperature_info = self.get_cpu_temperature()
            if temperature_info[0] == -1.0:
                send_cpu_except_warning_msg()
                time.sleep(10)
                continue

            for cpu in self.cpu_dict.values():
                cpu.temperature = temperature_info[cpu.idx]

                if cpu.high_temperature_trigger:
                    send_cpu_temperature_warning_msg(cpu.idx, cpu.temperature)

            time.sleep(TEMPERATURE_MONITOR_SAMPLING_INTERVAL)

    @staticmethod
    def get_cpu_temperature() -> dict[int, float]:
        if not hasattr(psutil, "sensors_temperatures"):
            return {0: -1.0}
        temps = psutil.sensors_temperatures()
        if not temps:
            return {0: -1.0}
        cpu_temperature_info: dict[int, float] = {}
        idx = 0
        for name, entries in temps.items():
            if name != "coretemp":
                continue
            for entry in entries:
                if not ("Package" in entry.label or "Package" in name):
                    continue
                cpu_temperature_info.update({idx: entry.current})
                idx += 1

        return cpu_temperature_info


def start_cpu_monitor_all():
    NUM_CPU = CPUInfo.get_cpu_num()
    if NUM_CPU is None:
        logger.error("Cannot get the number of CPU.")
        return

    cpu_monitor = CPUMonitor(NUM_CPU)
    cpu_monitor.start_monitor(cpu_monitor.cpu_monitor_thread)


if __name__ == "__main__":
    start_cpu_monitor_all()
