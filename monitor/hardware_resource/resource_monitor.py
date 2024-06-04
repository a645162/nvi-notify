# -*- coding: utf-8 -*-

import threading
import time

import psutil

from config.settings import (
    HARD_DISK_HIGH_PERCENTAGE_THRESHOLD,
    HARD_DISK_LOW_FREE_GB_THRESHOLD,
    HARD_DISK_MONITOR_SAMPLING_INTERVAL,
    HARD_DISK_MOUNT_POINT,
    WEBHOOK_SLEEP_TIME_END,
    WEBHOOK_SLEEP_TIME_START,
    is_within_time_range,
)
from utils.converter import convert_bytes_to_gb, get_human_str_from_byte
from utils.logs import get_logger
from notify.send_task_msg import send_hard_disk_high_occupancy_warning_msg

logger = get_logger()


class Memory:
    @staticmethod
    def convert_mem_to_str(mem_bytes: int) -> str:
        mem_gb = convert_bytes_to_gb(mem_bytes)
        return f"{mem_gb:.1f}"

    @staticmethod
    def get_memory_info():
        return psutil.virtual_memory()

    @staticmethod
    def get_swap_memory_info():
        return psutil.swap_memory()


class HardDisk:
    def __init__(self, mountpoint="/") -> None:
        self.disk_usage = psutil.disk_usage(mountpoint)

    def get_total_bytes(self) -> int:
        return self.disk_usage.total

    def get_used_bytes(self) -> int:
        return self.disk_usage.used

    def get_free_bytes(self) -> int:
        return self.disk_usage.free

    def get_percentage(self) -> float:
        return self.disk_usage.percent

    def get_total_for_human(self) -> str:
        return get_human_str_from_byte(self.disk_usage.total)

    def get_used_for_human(self) -> str:
        return get_human_str_from_byte(self.disk_usage.used)

    def get_free_for_human(self) -> str:
        return get_human_str_from_byte(self.disk_usage.free)

    def get_total_GB(self) -> float:
        return convert_bytes_to_gb(self.disk_usage.total)

    def get_free_GB(self) -> float:
        return convert_bytes_to_gb(self.disk_usage.free)


class HardDiskMonitor:
    def __init__(self, mountpoint: str):
        self.mountpoint: str = mountpoint
        self.harddisk = HardDisk(mountpoint)
        self.hard_disk_name = "system" if mountpoint == "/" else "data"
        self.high_percentage_trigger: bool = False
        self.low_free_trigger: bool = False
        self.thread = None

        self.high_percentage_threshold = (
            85 if mountpoint == "/" else HARD_DISK_HIGH_PERCENTAGE_THRESHOLD
        )
        self.low_free_threshold = (
            50 if mountpoint == "/" else HARD_DISK_LOW_FREE_GB_THRESHOLD
        )

        self.send_warning_msg_trigger: bool = False

        self.total_GB: float = 0.0
        self._percentage: float = 0.0
        self._free_GB: float = 999999.0

    monitor_thread_work = False

    def start_monitor(self):
        def harddisk_monitor_thread():
            logger.info(f"Hrad disk {self.mountpoint} monitor start")
            while monitor_thread_work:
                self.harddisk = HardDisk(self.mountpoint)
                self.percentage = self.harddisk.get_percentage()
                self.free_GB = self.harddisk.get_free_GB()
                self.total_GB = self.harddisk.get_total_GB()

                if self.hard_disk_name == "system":
                    self.send_warning_msg_trigger = self.low_free_trigger
                elif self.hard_disk_name == "data":
                    self.send_warning_msg_trigger = (
                        self.high_percentage_trigger and self.low_free_trigger
                    )
                if self.send_warning_msg_trigger:
                    logger.info("硬盘容量不足！")
                if self.send_warning_msg_trigger and not is_within_time_range(
                    WEBHOOK_SLEEP_TIME_START, WEBHOOK_SLEEP_TIME_END
                ):
                    send_hard_disk_high_occupancy_warning_msg(
                        self.hard_disk_name,
                        self.mountpoint,
                        self.total_GB,
                        self.free_GB,
                        self.percentage,
                    )

                time.sleep(HARD_DISK_MONITOR_SAMPLING_INTERVAL)

            logger.info(f"Hrad disk {self.mountpoint} monitor stop")

        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=harddisk_monitor_thread)
        monitor_thread_work = True
        self.thread.start()
        # self.thread.join()

    @property
    def percentage(self):
        return self._percentage

    @percentage.setter
    def percentage(self, cur_percentage):
        self.high_percentage_trigger = cur_percentage > self.high_percentage_threshold
        self._percentage = cur_percentage

    @property
    def free_GB(self):
        return self._free_GB

    @free_GB.setter
    def free_GB(self, cur_free_GB):
        self.low_free_trigger = (cur_free_GB < self.low_free_threshold) and (cur_free_GB < self._free_GB)
        self._free_GB = cur_free_GB


def start_resource_monitor_all():
    if HARD_DISK_MOUNT_POINT is None:
        logger.error("Cannot get the mountpoint of hard disk.")
        return

    for mountpoint in HARD_DISK_MOUNT_POINT:
        hard_disk_monitor = HardDiskMonitor(mountpoint)
        hard_disk_monitor.start_monitor()


if __name__ == "__main__":
    start_resource_monitor_all()
