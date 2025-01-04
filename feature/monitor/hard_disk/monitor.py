# -*- coding: utf-8 -*-

import time

import humanfriendly

from config.config_utils import is_webhook_sleep_time
from config.settings import (
    HARD_DISK_MONITOR_PASS_ROOT_CHECK,
    HARD_DISK_MONITOR_SAMPLING_INTERVAL,
    HARD_DISK_MOUNT_POINT,
    USERS,
)
from config.user_info import UserInfo
from feature.global_variable.disk_status import disk_info_response_dict
from feature.monitor.hard_disk import DiskPurpose, HardDisk
from feature.monitor.monitor import Monitor
from feature.utils import (
    cat_info,
    do_command,
    get_logger,
    check_is_linux,
    check_is_root,
    get_os_release_id,
)
from feature.webhook.msg_handler import MessageHandler

logger = get_logger()


class HardDiskMonitor(Monitor):
    def __init__(self, mount_points: set):
        """
        初始化硬盘监控器

        Args:
            mount_points (set): 要监控的挂载点集合
        """
        super().__init__("HardDisk")
        self.mount_points: set = mount_points
        self.hard_disk_dict: dict[str, HardDisk] = self.get_hard_disk_obj()

    def get_hard_disk_obj(self) -> dict[str, HardDisk]:
        """为每个挂载点创建 HardDisk 对象并返回字典

        Returns:
            dict[str, HardDisk]: 以挂载点为键，HardDisk 对象为值的字典

        Raises:
            ValueError: 如果挂载点无效
            RuntimeError: 如果获取磁盘信息失败
        """
        hard_disk_dict: dict[str, HardDisk] = {}

        try:
            machine_hard_disk_dict = self.get_machine_hard_disk_dict()

            if not machine_hard_disk_dict:
                logger.error("无法获取机器磁盘信息")
                raise RuntimeError("无法获取机器磁盘信息")

            for mount_point in self.mount_points:
                if mount_point not in machine_hard_disk_dict:
                    logger.error(f"无效的挂载点: {mount_point}")
                    raise ValueError(f"{mount_point} 不是有效的挂载点")

                disk_name = machine_hard_disk_dict[mount_point]
                logger.debug(f"创建硬盘对象: {disk_name} @ {mount_point}")

                hard_disk_dict[mount_point] = HardDisk(disk_name, mount_point)
                logger.info(f"成功初始化硬盘监控: {mount_point}")

            return hard_disk_dict

        except Exception as e:
            logger.error(f"初始化硬盘对象时出错: {e}")
            raise

    def update_disk_detail_info(self) -> None:
        """通过运行 `df -h` 命令更新每个硬盘的详细信息

        Raises:
            RuntimeError: 如果命令执行失败
        """
        command = "df -lh"
        try:
            result_code, results, error = do_command(command)

            if result_code != 0:
                logger.error(f"执行 df 命令失败: {error}")
                raise RuntimeError(f"无法获取磁盘信息: {error}")

            detail_infos = results.split("\n")[1:]  # 忽略标题行

            for line in detail_infos:
                fields = line.split()
                if len(fields) != 6:
                    continue

                mount_point = fields[5]
                if mount_point in self.mount_points:
                    self.hard_disk_dict[mount_point].update_info(fields)
                    logger.info(f'[硬盘"{mount_point}"]获取容量信息成功')

            self.__generate_api_response_data()

        except Exception as e:
            logger.error(f"更新磁盘信息时出错: {e}")
            raise

    def __generate_api_response_data(self):
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
        disk_info_response_dict.clear()
        disk_info_response_dict.update(disk_info_dict)

    def hard_disk_monitor_thread(self):
        """
        在单独线程中监控硬盘，检查警告并发送通知
        """
        disk_warning_cnt = {}
        while self.monitor_thread_work:
            self.update_disk_detail_info()
            for mount_point, hard_disk in self.hard_disk_dict.items():
                if not hard_disk.size_warning_trigger:
                    continue
                logger.warning(f"[硬盘{mount_point}]容量不足！")

                if not is_webhook_sleep_time():
                    disk_warning_cnt[mount_point] = (
                        disk_warning_cnt.get(mount_point, 0) + 1
                    )
                    if disk_warning_cnt[mount_point] % 4 == 2:
                        logger.warning(f"[硬盘{mount_point}]开始扫描目录占用容量...")
                        self.get_user_dir_size_info(hard_disk)
                        disk_warning_cnt[mount_point] = 0

                    MessageHandler.enqueue_hard_disk_warning_msg(hard_disk.disk_info)

            time.sleep(HARD_DISK_MONITOR_SAMPLING_INTERVAL)

    def get_user_dir_size_info(self, hard_disk: HardDisk) -> None:
        """
        如果硬盘用于数据存储，则获取用户目录的大小信息

        Args:
            hard_disk (HardDisk): 要检查的硬盘对象
        """
        if hard_disk.purpose != DiskPurpose.DATA:
            return

        scan_path = ""

        if hard_disk.mount_point == "/":
            # root path is not allowed to scan
            return

        if get_os_release_id() == "centos":
            if hard_disk.mount_point == "/home":
                scan_path = "~/data"
            else:
                raise ValueError("Error hard disk mount point!")
        elif get_os_release_id() == "ubuntu":
            if "hdd" in hard_disk.mount_point:
                if hard_disk.mount_point[-1] == "1":
                    scan_path = f"{hard_disk.mount_point}/data"
                elif hard_disk.mount_point[-1] == "2":
                    scan_path = f"{hard_disk.mount_point}/data1"
            else:
                scan_path = hard_disk.mount_point
        else:
            raise ValueError("Error hard disk mount point!")

        scan_path = scan_path.strip()
        if len(scan_path) == 0:
            return

        du_command = "du -sh *"
        # du_command = "du -lh --max-depth=1"

        command_args: str = f"cd {scan_path} && {du_command}"
        # print(command_args)

        retry_count = 0
        while retry_count < 5:
            try:
                result_code, results, _ = do_command(command_args)
                if result_code == 0:
                    break
            except Exception as e:
                logger.warning(f"执行命令出错: {e}")

            if retry_count == 5:
                logger.error("超过最大重试次数")
                return
            retry_count += 1

            logger.warning(f"正在进行第 {retry_count} 次重试...")

        detail_dirs_info = results.strip().split("\n")
        self.parse_dir_size_info(detail_dirs_info, hard_disk)

    def get_machine_hard_disk_dict(self) -> dict[str, str]:
        """
        使用 `lsblk` 命令获取机器上的硬盘字典

        Returns:
            dict[str, str]: 以挂载点为键，磁盘名称为值的字典
        """
        machine_all_hard_disk_dict = {}
        results = cat_info("/proc/mounts")
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
    def parse_dir_size_info(detail_dirs_info: list[str], hard_disk: HardDisk):
        """
        解析目录大小信息并在必要时发送警告

        Args:
            detail_dirs_info (list[str]): 目录大小信息字符串列表
            hard_disk (HardDisk): 要检查的硬盘对象
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
            user_dir = hard_disk.handle_disk_info_mountpoint(hard_disk.mount_point)

            logger.warning(
                f"[硬盘\"{hard_disk.mount_point}\"]{user.name_cn}的个人目录'{user_dir}'占用{dir_size}"
            )

            MessageHandler.enqueue_hard_disk_warning_msg_to_user(
                hard_disk.disk_info, user_dir, dir_size, user
            )


def start_resource_monitor_all():
    """
    启动所有资源监控，特别是硬盘监控
    """
    if HARD_DISK_MOUNT_POINT is None:
        logger.warning("无法获取硬盘挂载点")
        return

    if not check_is_linux():
        logger.warning("资源监控仅支持 Linux 系统")
        return

    if not HARD_DISK_MONITOR_PASS_ROOT_CHECK and not check_is_root():
        logger.warning("资源监控仅支持 root 用户启动")
        return

    hard_disk_monitor = HardDiskMonitor(HARD_DISK_MOUNT_POINT)
    hard_disk_monitor.start_monitor(hard_disk_monitor.hard_disk_monitor_thread)


if __name__ == "__main__":
    start_resource_monitor_all()
