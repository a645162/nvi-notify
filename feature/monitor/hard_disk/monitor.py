# -*- coding: utf-8 -*-
import time
from pathlib import Path

import humanfriendly

from config.config_utils import is_webhook_sleep_time
from config.settings import (
    DEBUG_MODE,
    HARD_DISK_MONITOR_PASS_ROOT_CHECK,
    HARD_DISK_MONITOR_SAMPLING_INTERVAL,
    HARD_DISK_MOUNT_POINT,
    USERS,
)
from config.user_info import UserInfo
from feature.group_center.data_manager import DataManager
from feature.monitor.hard_disk.hard_disk import DiskPurpose, HardDisk
from feature.monitor.monitor import Monitor
from feature.utils.common_utils import cat_info, do_command
from feature.utils.logs import get_logger
from feature.utils.system import check_is_linux, check_is_root
from feature.webhook.msg_handler import MessageHandler
from toolkit.user_login import get_user_last_login

logger = get_logger()


class HardDiskMonitor(Monitor):
    def __init__(self, mount_points: set):
        """
        Initialize the HardDiskMonitor with the specified mount points.

        Parameters:
        mount_points (set): A set or list of mount points to monitor.
        """
        super().__init__("HardDisk")
        self.mount_points: set = mount_points
        self.hard_disk_dict: dict[str, HardDisk] = self.get_hard_disk_obj()

    def get_hard_disk_obj(self) -> dict[str, HardDisk]:
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
                logger.warning(f"{mount_point} is not a valid mount point")
                continue

            hard_disk_dict[mount_point] = HardDisk(
                machine_hard_disk_dict[mount_point], mount_point
            )

        return hard_disk_dict

    def update_disk_detail_info(self):
        """
        Update the detailed information of each hard disk by running the `df -h` command.
        """
        command = "df -lh"
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
        DataManager().disk_info_response_dict.clear()
        DataManager().disk_info_response_dict.update(disk_info_dict)

    def hard_disk_monitor_thread(self) -> None:
        """
        Monitor the hard disk in a separate thread, checking for warnings and sending notifications.
        """
        disk_warning_cnt = {}
        while self.monitor_thread_work:
            self.update_disk_detail_info()
            for mount_point, hard_disk in self.hard_disk_dict.items():
                if not hard_disk.size_warning_trigger:
                    continue
                logger.warning(f"[硬盘{mount_point}]容量不足！")

                # DEBUG模式下忽略夜间休息静默模式
                should_send_notification = DEBUG_MODE or not is_webhook_sleep_time()
                
                if should_send_notification:
                    disk_warning_cnt[mount_point] = (
                        disk_warning_cnt.get(mount_point, 0) + 1
                    )
                    
                    # 如果连续警告超过24次，清理用户缓存
                    if disk_warning_cnt[mount_point] >= 24:
                        logger.warning(f"[硬盘{mount_point}]连续警告超过24次，开始清理用户缓存...")
                        self.clean_user_cache(hard_disk)
                        disk_warning_cnt[mount_point] = 0
                    
                    # 扫描目录（不清零，等达到24次再清零）
                    should_scan_dirs = (
                        DEBUG_MODE or
                        disk_warning_cnt[mount_point] == 1 or
                        disk_warning_cnt[mount_point] % 8 == 0
                    )
                    
                    if should_scan_dirs:
                        logger.warning(f"[硬盘{mount_point}]开始扫描目录占用容量...")
                        self.get_user_dir_size_info(hard_disk)

                    MessageHandler.enqueue_hard_disk_warning_msg(hard_disk.disk_info)

            time.sleep(HARD_DISK_MONITOR_SAMPLING_INTERVAL)

    def clean_user_cache(self, hard_disk: HardDisk) -> None:
        """
        Clean user cache when the monitored disk is full.
        - If monitoring /home: clean /home user cache
        - If monitoring / (no /home exists): clean /home user cache

        Parameters:
        hard_disk (HardDisk): The HardDisk object representing the hard disk to be cleaned.
        """
        # 根据当前监控的挂载点决定清理目标
        mount_point = hard_disk.mount_point.strip()
        
        # 检查是否存在 /home 挂载点（配置中）
        home_in_config = "/home" in HARD_DISK_MOUNT_POINT
        
        if home_in_config and "/home" in mount_point:
            # 有 /home 配置且监控的是 /home，清理 /home 用户缓存
            clean_path = "/home"
        elif not home_in_config and mount_point == "/":
            # 无 /home 配置，监控的是 /，清理 /home 用户缓存
            clean_path = "/home"
        else:
            # 其他情况不清理
            return

        if not Path(clean_path).exists():
            logger.warning(f"[清理] {clean_path} 不存在，跳过清理")
            return

        # 清理所有用户的 .vscode-server 和 .cache
        for user_name, user_info in USERS.items():
            user_home = user_info.home

            # 确保用户目录在清理路径下
            if not user_home.startswith(clean_path):
                continue

            # 清理 .vscode-server
            vscode_server_path = f"{user_home}/.vscode-server"
            if Path(vscode_server_path).exists():
                try:
                    result_code, _, _ = do_command(f"rm -rf {vscode_server_path}")
                    if result_code == 0:
                        logger.info(f"[清理] 已删除 {user_name} 的 .vscode-server")
                        MessageHandler.enqueue_hard_disk_warning_msg(
                            f"[系统自动清理] 已删除用户 {user_name} 的 .vscode-server 缓存"
                        )
                except Exception as e:
                    logger.warning(f"[清理] 删除 {user_name} 的 .vscode-server 失败: {e}")

            # 清理 .cache
            cache_path = f"{user_home}/.cache"
            if Path(cache_path).exists():
                try:
                    result_code, _, _ = do_command(f"rm -rf {cache_path}")
                    if result_code == 0:
                        logger.info(f"[清理] 已删除 {user_name} 的 .cache")
                        MessageHandler.enqueue_hard_disk_warning_msg(
                            f"[系统自动清理] 已删除用户 {user_name} 的 .cache 缓存"
                        )
                except Exception as e:
                    logger.warning(f"[清理] 删除 {user_name} 的 .cache 失败: {e}")

    def get_user_dir_size_info(self, hard_disk: HardDisk) -> None:
        """
        Get the size information of user directories if the hard disk is for data storage.

        Parameters:
        hard_disk (HardDisk): The HardDisk object representing the hard disk to be checked.
        """
        # 硬盘爆满时扫描所有硬盘，不管用途是什么
        if hard_disk.purpose != DiskPurpose.DATA:
            logger.info(f"[硬盘{hard_disk.mount_point}]硬盘用途不是DATA，但容量不足，继续扫描")

        scan_path = ""
        hd_mp = hard_disk.mount_point.strip()

        if hd_mp == "/" or len(hd_mp) == 0:
            # 检查是否为sudo权限，只有sudo权限才能扫描/home目录
            if not check_is_root():
                logger.info(f"[硬盘{hd_mp}]非root权限，跳过根目录扫描")
                return
            else:
                logger.info(f"[硬盘{hd_mp}]root权限下允许扫描根目录")

        if hd_mp == "/":
            # 根目录扫描 /home 目录
            scan_path = "/home"
        elif "hdd" in hd_mp:
            if hd_mp[-1] == "1":
                scan_path = f"{hd_mp}/data"
            elif hd_mp[-1] == "2":
                scan_path = f"{hd_mp}/data1"
        else:
            scan_path = hd_mp
        
        logger.info(f"[硬盘{hd_mp}]开始扫描路径: {scan_path}")
        
        # 检查扫描路径是否存在
        scan_path_obj = Path(scan_path)
        if not scan_path_obj.exists():
            logger.warning(f"[硬盘{hd_mp}]扫描路径不存在: {scan_path}")
            return
        if not scan_path_obj.is_dir():
            logger.warning(f"[硬盘{hd_mp}]扫描路径不是目录: {scan_path}")
            return

        du_command = "du -sh *"
        # du_command = "du -lh --max-depth=1"

        command_args: str = f"cd {scan_path} && {du_command}"
        # print(command_args)

        retry_count = 0
        results = ""
        while retry_count < 5:
            try:
                result_code, results, _ = do_command(command_args)
                if result_code == 0:
                    break  # 命令执行成功，退出循环
            except Exception as e:
                logger.warning(f"Error executing command: {e}")

            retry_count += 1
            if retry_count == 5:
                logger.error("Max retries exceeded.")
                return

            logger.warning(f"Retry {retry_count}-th in progress...")

        logger.info(f"[硬盘{hd_mp}]扫描完成，开始解析目录信息...")
        detail_dirs_info = results.strip().split("\n")
        self.parse_dir_size_info(detail_dirs_info, hard_disk, scan_path)

    def get_machine_hard_disk_dict(self) -> dict[str, str]:
        """
        Retrieve the dict of hard disks on the machine using `lsblk` command.

        Returns:
        machine_all_hard_disk_dict (dict[str, str]): A dictionary with `mount point` as keys
            and `disk name` as values.
        """
        machine_all_hard_disk_dict = {}
        results = cat_info(Path("/proc/mounts"))
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

    def parse_dir_size_info(self, detail_dirs_info: list[str], hard_disk: HardDisk, scan_path: str) -> None:
        """
        Parse the directory size information and send warnings if necessary.

        Parameters:
        detail_dirs_info (list[str]): A list of directory size information strings.
        hard_disk (HardDisk): The HardDisk object representing the hard disk to be checked.
        """
        user_size_list = []
        total_dirs = 0
        matched_users = 0
        large_dirs = 0
        
        logger.info(f"[硬盘{hard_disk.mount_point}]开始解析扫描结果，共{len(detail_dirs_info)}行数据")
        
        for lines in detail_dirs_info:
            if len(lines) == 0:
                continue
                
            total_dirs += 1

            try:
                dir_size, dir_path = lines.split()
                dir_size_bytes = humanfriendly.parse_size(dir_size, binary=True)
                
                # 只处理大于1GB的目录
                if dir_size_bytes < humanfriendly.parse_size("1GB", binary=True):
                    continue
                    
                large_dirs += 1
                logger.info(f"[硬盘{hard_disk.mount_point}]发现大目录: {dir_path} - {dir_size}")

                user = UserInfo.find_user_by_path(USERS, dir_path)
                if user is None:
                    logger.debug(f"[硬盘{hard_disk.mount_point}]目录 {dir_path} 未匹配到用户")
                    continue
                    
                matched_users += 1
                user_dir = hard_disk.handle_disk_info_mountpoint(hard_disk.mount_point)

                # 记录用户和目录大小信息
                user_size_list.append({
                    "user": user,
                    "user_name_eng": user.name_eng,
                    "dir_name": user_dir,
                    "dir_size": dir_size,
                    "dir_size_bytes": dir_size_bytes
                })

                logger.info(f"[硬盘{hard_disk.mount_point}]匹配用户: {user.name_cn} - 目录: {dir_path} - 大小: {dir_size}")
            except Exception as e:
                logger.warning(f"[硬盘{hard_disk.mount_point}]解析目录信息失败: {lines}, 错误: {e}")

        logger.info(f"[硬盘{hard_disk.mount_point}]扫描统计: 总目录数={total_dirs}, 大目录(>1GB)={large_dirs}, 匹配用户={matched_users}")

        # 获取用户最后登录日期的辅助函数
        def get_user_last_login_date(username: str) -> str:
            """获取用户最后登录日期，只返回日期部分"""
            try:
                login_info = get_user_last_login(username, sudo=True)
                if login_info.login_time:
                    return login_info.login_time.strftime("%Y-%m-%d")
                return "从未登录"
            except Exception as e:
                logger.debug(f"获取用户 {username} 最后登录日期失败: {e}")
                return "未知"

        # 如果有用户数据，发送群组消息（包含前10名）和个人消息（只给前三名）
        if user_size_list:
            # 按目录大小排序
            user_size_list.sort(key=lambda x: x["dir_size_bytes"], reverse=True)
            
            # 构建前10名用户排名信息
            rank_message = "📊【硬盘使用情况排名】\n"
            for i, user_info in enumerate(user_size_list[:10], 1):
                user = user_info["user"]
                dir_name = user_info["dir_name"]
                dir_size = user_info["dir_size"]
                # 获取用户最后登录日期
                last_login_date = get_user_last_login_date(user.name_eng)
                rank_message += f"{i}. {user.name_cn} - {dir_size} ({dir_name}) - 最后登录: {last_login_date}\n"

            logger.info(f"[硬盘{hard_disk.mount_point}]发送排名信息: {rank_message}")

            # 发送群组消息，包含前10名用户排名
            MessageHandler.enqueue_hard_disk_warning_msg(
                hard_disk.disk_info, rank_message
            )
            
            # 只给前三名用户发送个人消息
            for i, user_info in enumerate(user_size_list[:3], 1):
                user = user_info["user"]
                dir_name = user_info["dir_name"]
                dir_size = user_info["dir_size"]
                dir_size_bytes = user_info["dir_size_bytes"]
                
                # 如果目录大于10GB，发送个人警告
                if dir_size_bytes >= humanfriendly.parse_size("10GB", binary=True):
                    # 获取用户最后登录日期
                    last_login_date = get_user_last_login_date(user.name_eng)
                    logger.warning(
                        f"[硬盘\"{hard_disk.mount_point}\"]{user.name_cn}的个人目录'{dir_name}'占用{dir_size}，最后登录: {last_login_date}"
                    )

                    MessageHandler.enqueue_hard_disk_warning_msg_to_user(
                        hard_disk.disk_info, (dir_name, dir_size, last_login_date), user
                    )
        else:
            logger.info(f"[硬盘{hard_disk.mount_point}]未找到匹配的用户目录数据")


def start_resource_monitor_all() -> None:
    """
    Start monitoring all resources, specifically the hard disk.
    """
    if HARD_DISK_MOUNT_POINT is None:
        logger.warning("Cannot get the mountpoint of hard disk.")
        return

    if not check_is_linux():
        logger.warning("Resource monitor only support Linux system.")
        return

    if not HARD_DISK_MONITOR_PASS_ROOT_CHECK and not check_is_root():
        logger.warning("Resource monitor only support root user.")
        return

    # 优先检测是否存在 /home 挂载点
    mount_points_to_monitor = set()
    
    # 解析配置的挂载点（支持 "/, /mnt/hdd1" 格式）
    if isinstance(HARD_DISK_MOUNT_POINT, str):
        # 将字符串 "/, /mnt/hdd1" 转换为集合
        configured_mount_points = set(
            mp.strip() for mp in HARD_DISK_MOUNT_POINT.split(",") if mp.strip()
        )
    else:
        configured_mount_points = set(HARD_DISK_MOUNT_POINT) if HARD_DISK_MOUNT_POINT else set()
    
    # 添加 /home 到监控列表（如果配置中有）
    if "/home" in configured_mount_points:
        mount_points_to_monitor.add("/home")
        logger.info("Found /home mount point, will monitor /home")
    
    # 添加 / 到监控列表（如果配置中有且没有 /home）
    if "/" in configured_mount_points and "/home" not in mount_points_to_monitor:
        mount_points_to_monitor.add("/")
        logger.info("Found / mount point, will monitor / (system disk)")
    
    # 添加其他配置的挂载点（如 /mnt/hdd1）
    for mp in configured_mount_points:
        if mp != "/" and mp != "/home":
            mount_points_to_monitor.add(mp)
            logger.info(f"Found additional mount point: {mp}")

    if not mount_points_to_monitor:
        logger.warning("Cannot get the mountpoint of hard disk.")
        return

    hard_disk_monitor = HardDiskMonitor(mount_points_to_monitor)
    hard_disk_monitor.start_monitor(hard_disk_monitor.hard_disk_monitor_thread)


if __name__ == "__main__":
    start_resource_monitor_all()
