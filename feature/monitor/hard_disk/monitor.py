import time
from pathlib import Path

import humanfriendly

from feature.config import config_utils, settings, user_info
from feature.group_center import data_manager
from feature.monitor import base
from feature.monitor.hard_disk import hard_disk
from feature.utils import common_utils, logs, system
from feature.webhook import msg_handler

logger = logs.get_logger()
data_manager_ins = data_manager.get_data_manager()


class HardDiskMonitor(base.MonitorBase):
    def __init__(self, mount_points: set) -> None:
        """
        Initialize the HardDiskMonitor with the specified mount points.

        Parameters:
        mount_points (set): A set or list of mount points to monitor.
        """
        super().__init__("HardDisk")
        self.mount_points: set = mount_points
        self.hard_disk_dict: dict[str, hard_disk.HardDisk] = self.get_hard_disk_obj()

    def get_hard_disk_obj(self) -> dict[str, hard_disk.HardDisk]:
        """
        Create HardDisk objects for each mount point and return them in a dictionary.

        Returns:
        hard_disk_dict[str, HardDisk]: A dictionary with mount points as keys
            and HardDisk objects as values.
        """
        hard_disk_dict = {}
        machine_hard_disk_dict = self.get_machine_hard_disk_dict()
        for mount_point in self.mount_points:
            if mount_point not in machine_hard_disk_dict:
                raise Exception(f"{mount_point} is not a valid mount point")
            hard_disk_dict[mount_point] = hard_disk.HardDisk(
                machine_hard_disk_dict[mount_point], mount_point
            )

        return hard_disk_dict

    def update_disk_detail_info(self) -> None:
        """
        Update the detailed information of each hard disk by running the `df -h` command.
        """
        command = "df -lh"
        _, results, _ = common_utils.do_command(command)
        detail_infos = results.split("\n")

        for i, line in enumerate(detail_infos):
            fields = line.split()
            if i == 0 or len(fields) != 6:  # ignore title line
                continue
            mount_point = fields[5]
            if mount_point in self.mount_points:
                self.hard_disk_dict[mount_point].update_info(fields)
                logger.info(f'[硬盘"{mount_point}"]获取容量信息成功')

        self.__generate_api_response_data()

    def __generate_api_response_data(self) -> None:
        disk_info_dict = {}

        for mount_point, disk_obj in self.hard_disk_dict.items():
            disk_info_dict[mount_point] = {
                "mountPoint": mount_point,
                "usedPercentage": disk_obj.percentage_used_int,
                "usedStr": disk_obj.used_str,
                "freeStr": disk_obj.free_str,
                "totalStr": disk_obj.total_str,
                "triggerHighPercentageUsed": disk_obj.high_percentage_used_trigger,
                "triggerLowFreeBytes": disk_obj.low_free_bytes_trigger,
                "triggerSizeWarning": disk_obj.size_warning_trigger,
                "type": disk_obj.type.name,
                "purpose": disk_obj.purpose_cn.value,
            }
        data_manager_ins.disk_info_response_dict.clear()
        data_manager_ins.disk_info_response_dict.update(disk_info_dict)

    def hard_disk_monitor_thread(self) -> None:
        """
        Monitor the hard disk in a separate thread, checking for warnings and sending notifications.
        """
        disk_warning_cnt = {}
        while self.monitor_thread_work:
            self.update_disk_detail_info()
            for mount_point, disk in self.hard_disk_dict.items():
                if not disk.size_warning_trigger:
                    continue
                logger.warning(f"[硬盘{mount_point}]容量不足！")

                if not config_utils.is_webhook_sleep_time():
                    disk_warning_cnt[mount_point] = (
                        disk_warning_cnt.get(mount_point, 0) + 1
                    )
                    if disk_warning_cnt[mount_point] % 4 == 2:
                        logger.warning(f"[硬盘{mount_point}]开始扫描目录占用容量...")
                        self.get_user_dir_size_info(disk)
                        disk_warning_cnt[mount_point] = 0

                    msg_handler.MessageHandler.enqueue_hard_disk_warning_msg(disk.disk_info)

            time.sleep(settings.HARD_DISK_MONITOR_SAMPLING_INTERVAL)

    def get_user_dir_size_info(self, disk: hard_disk.HardDisk) -> None:
        """
        Get the size information of user directories if the hard disk is for data storage.

        Parameters:
        disk (hard_disk.HardDisk): The HardDisk object representing the hard disk to be checked.
        """
        if disk.purpose != hard_disk.DiskPurpose.DATA:
            return

        scan_path = ""
        hd_mp = disk.mount_point.strip()

        if hd_mp == "/" or len(hd_mp) == 0:
            # root path is not allowed to scan
            return

        if "hdd" in hd_mp:
            if hd_mp[-1] == "1":
                scan_path = f"{hd_mp}/data"
            elif hd_mp[-1] == "2":
                scan_path = f"{hd_mp}/data1"
        else:
            scan_path = hd_mp

        du_command = "du -sh *"
        # du_command = "du -lh --max-depth=1"

        command_args: str = f"cd {scan_path} && {du_command}"
        # print(command_args)

        retry_count = 0
        results = ""
        while retry_count < 5:
            try:
                result_code, results, _ = common_utils.do_command(command_args)
                if result_code == 0:
                    break  # 命令执行成功，退出循环
            except Exception as e:
                logger.warning(f"Error executing command: {e}")

            retry_count += 1
            if retry_count == 5:
                logger.error("Max retries exceeded.")
                return

            logger.warning(f"Retry {retry_count}-th in progress...")

        detail_dirs_info = results.strip().split("\n")
        self.parse_dir_size_info(detail_dirs_info, disk)

    def get_machine_hard_disk_dict(self) -> dict[str, str]:
        """
        Retrieve the dict of hard disks on the machine using `lsblk` command.

        Returns:
        machine_all_hard_disk_dict (dict[str, str]): A dictionary with `mount point` as keys
            and `disk name` as values.
        """
        machine_all_hard_disk_dict = {}
        results = common_utils.cat_info(Path("/proc/mounts"))
        for line in results.strip().split("\n"):
            mount_device = line.split(" ")

            if mount_device[1].startswith("/var/snap") or mount_device[2] != "ext4":
                continue

            mount_point = mount_device[1]

            disk_name = mount_device[0].split("/")[-1]
            if "nvme" in disk_name:
                disk_name = disk_name[:7]
            else:
                disk_name = disk_name[:3]

            machine_all_hard_disk_dict[mount_point] = disk_name

        return machine_all_hard_disk_dict

    @staticmethod
    def parse_dir_size_info(detail_dirs_info: list[str], disk: hard_disk.HardDisk) -> None:
        """
        Parse the directory size information and send warnings if necessary.

        Parameters:
        detail_dirs_info (list[str]): A list of directory size information strings.
        disk (HardDisk): The HardDisk object representing the hard disk to be checked.
        """
        for lines in detail_dirs_info:
            if len(lines) == 0:
                continue

            dir_size, dir_path = lines.split()
            if humanfriendly.parse_size(
                dir_size, binary=True
            ) < humanfriendly.parse_size("10GB", binary=True):
                continue

            user = user_info.UserInfo.find_user_by_path(settings.USERS, dir_path)
            if user is None:
                continue
            user_dir = disk.handle_disk_info_mountpoint(disk.mount_point)

            logger.warning(
                f"[硬盘\"{disk.mount_point}\"]{user.name_cn}的个人目录'{user_dir}'占用{dir_size}"
            )

            msg_handler.MessageHandler.enqueue_hard_disk_warning_msg_to_user(
                disk.disk_info, (user_dir, dir_size), user
            )


def start_resource_monitor_all() -> None:
    """
    Start monitoring all resources, specifically the hard disk.
    """
    if settings.HARD_DISK_MOUNT_POINT is None:
        logger.warning("Cannot get the mountpoint of hard disk.")
        return

    if not system.check_is_linux():
        logger.warning("Resource monitor only support Linux system.")
        return

    if not settings.HARD_DISK_MONITOR_PASS_ROOT_CHECK and not system.check_is_root():
        logger.warning("Resource monitor only support root user.")
        return

    hard_disk_monitor = HardDiskMonitor(settings.HARD_DISK_MOUNT_POINT)
    hard_disk_monitor.start_monitor(hard_disk_monitor.hard_disk_monitor_thread)


if __name__ == "__main__":
    start_resource_monitor_all()
