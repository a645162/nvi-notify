# -*- coding: utf-8 -*-

import threading
import time
from typing import Union

from config.settings import get_settings
from feature.monitor.hard_disk.hard_disk import HardDisk
from feature.notify.send_task_msg import send_hard_disk_high_occupancy_warning_msg
from utils.logs import get_logger
from utils.utils import do_command

logger = get_logger()
settings = get_settings()


class HardDiskMonitor:
    def __init__(self, mount_points: Union[set, list]):
        self.mount_points: str = mount_points
        self.hard_disk_dict: dict[str, HardDisk] = self.get_hard_disk_obj()

        self.send_warning_msg_trigger: bool = False
        self.thread = None

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

    monitor_thread_work = False

    def start_monitor(self):
        def harddisk_monitor_thread():
            logger.info("Hrad disk monitor start")
            while monitor_thread_work:
                self.update_disk_detail_info()

                for hard_disk in self.hard_disk_dict.values():
                    if hard_disk.size_warning_trigger:
                        logger.info(f"[硬盘{hard_disk.mount_point}]容量不足！")
                        if not settings.is_webhook_sleep_time:
                            send_hard_disk_high_occupancy_warning_msg(
                                hard_disk.disk_info()
                            )
                time.sleep(settings.HARD_DISK_MONITOR_SAMPLING_INTERVAL)

            logger.info("Hrad disk monitor stop")

        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=harddisk_monitor_thread)
        monitor_thread_work = True
        self.thread.start()
        # self.thread.join()

    def get_smart_info(device) -> None | str:
        if not settings.SUDO_PERMISSION:
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
    if settings.HARD_DISK_MOUNT_POINT is None:
        logger.error("Cannot get the mountpoint of hard disk.")
        return

    hard_disk_monitor = HardDiskMonitor(settings.HARD_DISK_MOUNT_POINT)
    hard_disk_monitor.start_monitor()


if __name__ == "__main__":
    start_resource_monitor_all()
