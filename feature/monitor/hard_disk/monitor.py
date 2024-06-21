# -*- coding: utf-8 -*-

import time
from typing import Tuple, Union

import humanfriendly

from config.settings import (
    HARD_DISK_MONITOR_SAMPLING_INTERVAL,
    HARD_DISK_MOUNT_POINT,
    USERS,
)
from config.user_info import UserInfo
from config.utils import is_webhook_sleep_time
from feature.monitor.hard_disk.hard_disk import DiskPurpose, HardDisk
from feature.monitor.monitor import Monitor
from feature.notify.message_handler import MessageHandler
from feature.utils.logs import get_logger
from feature.utils.utils import do_command

logger = get_logger()


class HardDiskMonitor(Monitor):
    def __init__(self, mount_points: Union[set, list]):
        """
        Initialize the HardDiskMonitor with the specified mount points.

        Parameters:
        mount_points (Union[set, list]): A set or list of mount points to monitor.
        """
        super().__init__("HardDisk")
        self.mount_points: Union[set, list] = mount_points
        self.hard_disk_dict: dict[str, HardDisk] = self.get_hard_disk_obj()

    def get_hard_disk_obj(self) -> dict[str, HardDisk]:
        """
        Create HardDisk objects for each mount point and return them in a dictionary.

        Returns:
        hard_disk_dict[str, HardDisk]: A dictionary with mount points as keys
            and HardDisk objects as values.
        """
        hard_disk_dict = {}
        for mount_point in self.mount_points:
            if mount_point not in self.get_machine_hard_disk_dict():
                raise Exception(f"{mount_point} is not a valid mount point")
            hard_disk_dict[mount_point] = HardDisk(mount_point)

        return hard_disk_dict

    def update_disk_detail_info(self):
        """
        Update the detailed information of each hard disk by running the `df -h` command.
        """
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
        """
        Monitor the hard disk in a separate thread, checking for warnings and sending notifications.
        """
        while self.monitor_thread_work:
            self.update_disk_detail_info()
            disk_warning_cnt = {}
            for mount_point, hard_disk in self.hard_disk_dict.items():
                if not hard_disk.size_warning_trigger:
                    continue
                logger.warning(f"[硬盘{mount_point}]容量不足！")

                if not is_webhook_sleep_time():
                    disk_warning_cnt[mount_point] = disk_warning_cnt.get(mount_point, 0) + 1
                    if disk_warning_cnt[mount_point] % 4 == 0:
                        logger.warning(f"[硬盘{mount_point}]开始扫描目录占用容量...")
                        self.get_user_dir_size_info(hard_disk)
                        disk_warning_cnt[mount_point] = 0

                    MessageHandler.enqueue_hard_disk_size_warning_msg(
                        hard_disk.disk_info
                    )

            time.sleep(HARD_DISK_MONITOR_SAMPLING_INTERVAL)

    def get_user_dir_size_info(self, hard_disk: HardDisk) -> None:
        """
        Get the size information of user directories if the hard disk is for data storage.

        Parameters:
        hard_disk (HardDisk): The HardDisk object representing the hard disk to be checked.
        """
        if hard_disk.purpose != DiskPurpose.DATA:
            return

        command_args: list[str] = ["du", "-sh"]
        
        if hard_disk.mount_point == "/home":
            command_args.append("~/data/*")
        else:
            command_args.append(f"{hard_disk.mount_point}/data/*")

        retry_count = 0
        while retry_count + 1 < 5:
            try:
                result_code, results, _ = do_command(command_args)
                if result_code == 0:
                    break  # 命令执行成功，退出循环
            except Exception as e:
                logger.warning(f"Error executing command: {e}")

            if retry_count == 5:
                logger.error("Max retries exceeded.")
                return

            logger.warning(f"Retry {retry_count}-th in progress...")

        detail_dirs_info = results.split("\n")
        self.parse_dir_size_info(detail_dirs_info, hard_disk.disk_info)

    def get_machine_hard_disk_dict(self) -> dict[str, str]:
        """
        Retrieve the dict of hard disks on the machine using `lsblk` command.

        Returns:
        machine_all_hard_disk_dict (dict[str, str]): A dictionary with `mount point` as keys
            and `disk name` as values.
        """
        machine_all_hard_disk_dict = {}
        command = "lsblk | grep disk"
        result_code, results, _ = do_command(command)
        if result_code != 0:
            return machine_all_hard_disk_dict

        detail_info = results.strip().split("\n")
        for disk in detail_info:
            disk_name, mount_point = self.parse_lsblk_result(disk)
            if len(disk_name) == 0 or len(mount_point) == 0:
                continue
            machine_all_hard_disk_dict[mount_point] = disk_name

        return machine_all_hard_disk_dict

    def parse_lsblk_result(self, line: str) -> Tuple[str, str]:
        """
        Parse the result of 'lsblk' command to extract `disk name` and `mount point`.

        Parameters:
        line (str): A line of output from the 'lsblk' command.

        Returns:
        Tuple[str, str]: A tuple containing the `disk name` and `mount point`.
        """
        line_unit = line.split()
        if len(line_unit) == 0:
            return "", ""

        name = line_unit[0]
        if len(name) == 0:
            return "", ""

        if len(line_unit) == 6:
            command = f"lsblk | grep {name}"
            result_code, results, _ = do_command(command)
            if result_code != 0:
                return "", ""

            results_units = results.strip().split("\n")
            for results_unit in results_units:
                results_unit = results_unit.split()
                if len(results_unit) != 7:
                    continue

                _mount_point = results_unit[-1].lower()
                if "boot" not in _mount_point and "swap" not in _mount_point:
                    mount_point = results_unit[-1]
                else:
                    mount_point = ""
                """ TODO: Hack implementation. Only for ubuntu22.04.
                """
                if _mount_point == "/var/snap/firefox/common/host-hunspell":
                    mount_point = "/"

        elif len(line_unit) == 7:
            mount_point = line_unit[-1]
        else:
            mount_point = ""

        return name, mount_point

    @staticmethod
    def parse_dir_size_info(detail_dirs_info: list[str], disk_info: str):
        """
        Parse the directory size information and send warnings if necessary.

        Parameters:
        detail_dirs_info (list[str]): A list of directory size information strings.
        disk_info (str): The disk information string for warning message.
        """
        for lines in detail_dirs_info:
            if len(lines) == 0:
                continue

            dir_size, dir_path = lines.split()
            if humanfriendly.parse_size(
                dir_size, binary=True
            ) < humanfriendly.parse_size("10GB", binary=True):
                continue

            user = UserInfo.find_user_by_path(USERS, dir_path)
            if user is None:
                continue

            MessageHandler.enqueue_hard_disk_size_warning_msg_to_user(
                disk_info, dir_path, dir_size, user
            )


def start_resource_monitor_all():
    """
    Start monitoring all resources, specifically the hard disk.
    """
    if HARD_DISK_MOUNT_POINT is None:
        logger.error("Cannot get the mountpoint of hard disk.")
        return

    hard_disk_monitor = HardDiskMonitor(HARD_DISK_MOUNT_POINT)
    hard_disk_monitor.start_monitor(hard_disk_monitor.harddisk_monitor_thread)


if __name__ == "__main__":
    start_resource_monitor_all()
