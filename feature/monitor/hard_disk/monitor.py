# -*- coding: utf-8 -*-

import time
from typing import Union

from config.settings import (
    HARD_DISK_MONITOR_SAMPLING_INTERVAL,
    HARD_DISK_MOUNT_POINT,
    SUDO_PERMISSION,
    is_webhook_sleep_time,
)
from feature.monitor.hard_disk.hard_disk import HardDisk
from feature.monitor.monitor import Monitor
from feature.notify.send_msg import send_hard_disk_size_warning_msg
from utils.logs import get_logger
from utils.utils import do_command

logger = get_logger()


class HardDiskMonitor(Monitor):
    def __init__(self, mount_points: Union[set, list]):
        self.mount_points: Union[set, list] = mount_points
        self.hard_disk_dict: dict[str, HardDisk] = self.get_hard_disk_obj()
        self.monitor_name = "Hard Disk"
        self._init_thread_()

    def get_hard_disk_obj(self) -> dict[str, HardDisk]:
        hard_disk_dict = {}
        for mount_point in self.mount_points:
            hard_disk_dict[mount_point] = HardDisk(mount_point)

        return hard_disk_dict

    def update_disk_detail_info(self):
        command = "df -h"
        _, results, _ = do_command(command)
        detail_infos = results.split("\n")

        for i, line in enumerate(detail_infos):
            fields = line.split()
            if i == 0 or len(fields) != 6:  # ignore title line
                continue
            mount_point = fields[5]
            if mount_point in self.mount_points:
                self.hard_disk_dict[mount_point].update_info(fields)
                logger.info(f'[硬盘"{mount_point}"]获取容量信息成功')

    def harddisk_monitor_thread(self):
        while self.monitor_thread_work:
            self.update_disk_detail_info()
            for hard_disk in self.hard_disk_dict.values():
                if not hard_disk.size_warning_trigger:
                    continue
                logger.info(f"[硬盘{hard_disk.mount_point}]容量不足！")
                if is_webhook_sleep_time():
                    continue
                send_hard_disk_size_warning_msg(hard_disk.disk_info())
            time.sleep(HARD_DISK_MONITOR_SAMPLING_INTERVAL)

    def get_smart_info(device) -> None | str:
        if not SUDO_PERMISSION:
            return

        command = f"sudo smartctl -H {device}"
        try:
            result_code, output_stdout, output_stderr = do_command(command)

            if result_code.returncode != 0:
                logger.warnning(f"Error running smartctl: {output_stderr}")
                return

            smart_info = output_stdout
            return smart_info

        except Exception as e:
            logger.warnning(f"An error occurred: {e}")
            return


def start_resource_monitor_all():
    if HARD_DISK_MOUNT_POINT is None:
        logger.error("Cannot get the mountpoint of hard disk.")
        return

    hard_disk_monitor = HardDiskMonitor(HARD_DISK_MOUNT_POINT)
    hard_disk_monitor.start_monitor(hard_disk_monitor.harddisk_monitor_thread)


if __name__ == "__main__":
    start_resource_monitor_all()
