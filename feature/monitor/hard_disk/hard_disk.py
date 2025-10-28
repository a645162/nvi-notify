from pathlib import Path

import humanfriendly

from config.settings import (
    HARD_DISK_HIGH_PERCENTAGE_THRESHOLD,
    HARD_DISK_LOW_FREE_GB_THRESHOLD,
    SUDO_PERMISSION,
)
from feature.monitor.monitor_enum import MonitorEnum
from feature.utils.common_utils import cat_info, do_command
from feature.utils.logs import get_logger

logger = get_logger()


class DiskPurpose(MonitorEnum):
    UNKNOWN = "unknown"
    SYSTEM = "system"
    DATA = "data"
    SYSTEM_CN = "系统盘"
    DATA_CN = "数据盘"


class DiskType(MonitorEnum):
    UNKNOWN = "unknown"
    SSD = "ssd"
    HDD = "hdd"
    SSD_CN = "固态硬盘"
    HDD_CN = "机械硬盘"


class HardDisk:
    def __init__(self, name: str, mount_point: str) -> None:
        """
        Args:
            name (str): disk name. such as 'sda1', 'nvme0n1'.
            mount_point (str): mount point. such as '/', '/home'.
        """
        self._name: str = ""
        self._mount_point: str = ""
        self._type: DiskType = DiskType.UNKNOWN
        self._purpose: DiskPurpose = DiskPurpose.UNKNOWN
        self._purpose_cn: DiskPurpose = DiskPurpose.UNKNOWN

        self._high_percentage_used_threshold: int = 0
        self._low_free_bytes_threshold: int = 0
        self._high_percentage_used_trigger: bool = False
        self._low_free_bytes_trigger: bool = False

        self._total_str: str = ""
        self._used_str: str = ""
        self._free_str: str = ""

        self._free_bytes: int = humanfriendly.parse_size(
            "1TB", binary=True
        )  # init max free bytes (1TiB)
        self._percentage_used_int: int = 0
        self._percentage_used_str: str = ""

        self._name: str = name
        # 使用 setter 来设置 mount_point，确保阈值正确设置
        self.mount_point = mount_point

    def update_info(self, info: list):
        self._total_str = info[1]
        self._used_str = info[2]
        self._free_str = info[3]
        self.percentage_used_str = info[4]

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        rotational = "0"
        if "nvme" not in value:
            rotational = cat_info(Path(f"/sys/block/{value}/queue/rotational")).strip()

        self.type = DiskType.HDD if rotational == "1" else DiskType.SSD
        self._name = value

    @property
    def used_str(self) -> str:
        return self._used_str

    @used_str.setter
    def used_str(self, value: str) -> None:
        self._used_str = value

    @property
    def total_str(self) -> str:
        return self._total_str

    @total_str.setter
    def total_str(self, value: str) -> None:
        self._total_str = value

    @property
    def free_str(self) -> str:
        return self._free_str

    @free_str.setter
    def free_str(self, value: str) -> None:
        self.free_bytes = humanfriendly.parse_size(value, binary=True)
        self._free_str = value

    @property
    def free_bytes(self) -> int:
        return self._free_bytes

    @free_bytes.setter
    def free_bytes(self, value: int) -> None:
        # 只有在阈值正确设置后才计算触发条件
        if self.low_free_bytes_threshold > 0:
            self.low_free_bytes_trigger = value < self.low_free_bytes_threshold
        else:
            # 如果阈值未正确设置，默认不触发
            self.low_free_bytes_trigger = False
        # self.low_free_bytes_trigger = (
        #     value < self.low_free_bytes_threshold
        # ) and (value < self._free_bytes)
        self._free_bytes = value

    @property
    def percentage_used_str(self) -> str:
        return self._percentage_used_str

    @percentage_used_str.setter
    def percentage_used_str(self, value: str) -> None:
        self.percentage_used_int = int(value[:-1])
        self._percentage_used_str = value

    @property
    def percentage_used_int(self) -> int:
        return self._percentage_used_int

    @percentage_used_int.setter
    def percentage_used_int(self, cur_percentage_used: int) -> None:
        # 只有在阈值正确设置后才计算触发条件
        if self.high_percentage_used_threshold > 0:
            self.high_percentage_used_trigger = (
                cur_percentage_used > self.high_percentage_used_threshold
            )
        else:
            # 如果阈值未正确设置，默认不触发
            self.high_percentage_used_trigger = False

        self._percentage_used_int = cur_percentage_used

    @property
    def mount_point(self) -> str:
        return self._mount_point

    @mount_point.setter
    def mount_point(self, value: str) -> None:
        if value == "/":
            self.purpose = DiskPurpose.SYSTEM
            self.purpose_cn = DiskPurpose.SYSTEM_CN
            self.high_percentage_used_threshold = 85
            self.low_free_bytes_threshold = humanfriendly.parse_size(
                "50GB", binary=True
            )
        else:
            self.purpose = DiskPurpose.DATA
            self.purpose_cn = DiskPurpose.DATA_CN
            self.high_percentage_used_threshold = HARD_DISK_HIGH_PERCENTAGE_THRESHOLD
            self.low_free_bytes_threshold = humanfriendly.parse_size(
                f"{HARD_DISK_LOW_FREE_GB_THRESHOLD}GB", binary=True
            )
        self._mount_point = value

    @property
    def purpose(self) -> DiskPurpose:
        """hard disk's purpose"""
        return self._purpose

    @purpose.setter
    def purpose(self, value: DiskPurpose) -> None:
        self._purpose = value

    @property
    def purpose_cn(self) -> DiskPurpose:
        """hard disk's purpose in Chinese"""
        return self._purpose_cn

    @purpose_cn.setter
    def purpose_cn(self, value: DiskPurpose) -> None:
        self._purpose_cn = value

    @property
    def type(self) -> DiskType:
        return self._type

    @type.setter
    def type(self, value: DiskType) -> None:
        self._type = value

    @property
    def high_percentage_used_threshold(self) -> int:
        return self._high_percentage_used_threshold

    @high_percentage_used_threshold.setter
    def high_percentage_used_threshold(self, value: int) -> None:
        self._high_percentage_used_threshold = value

    @property
    def low_free_bytes_threshold(self) -> int:
        return self._low_free_bytes_threshold

    @low_free_bytes_threshold.setter
    def low_free_bytes_threshold(self, value: int) -> None:
        self._low_free_bytes_threshold = value

    @property
    def high_percentage_used_trigger(self) -> bool:
        return self._high_percentage_used_trigger

    @high_percentage_used_trigger.setter
    def high_percentage_used_trigger(self, value: bool) -> None:
        self._high_percentage_used_trigger = value

    @property
    def low_free_bytes_trigger(self) -> bool:
        return self._low_free_bytes_trigger

    @low_free_bytes_trigger.setter
    def low_free_bytes_trigger(self, value: bool) -> None:
        self._low_free_bytes_trigger = value

    @property
    def size_warning_trigger(self) -> bool:
        if self.purpose == DiskPurpose.SYSTEM:
            return self.low_free_bytes_trigger
        elif self.purpose == DiskPurpose.DATA:
            return self.low_free_bytes_trigger and self.high_percentage_used_trigger
        return False

    @property
    def disk_info(self) -> str:
        return (
            f"{self.purpose_cn}(挂载点为{self.handle_disk_info_mountpoint(self.mount_point)})"
            f"剩余可用容量为{self.free_str}，总容量为{self.total_str}，"
            f"占用率为{self.percentage_used_str}\n"
        )

    def handle_disk_info_mountpoint(self, mount_point: str):
        linked_dict = {
            "/": "/",
            "/home": "/home",
            "/mnt/hdd1": "~/data",
            "/mnt/hdd2": "~/data1",
            "/mnt/code": "~/code",
            "/mnt/data": "~/data",
            "/mnt/datasets": "~/datasets",
        }
        return linked_dict[mount_point]

    def get_smart_info(self) -> str:
        if not SUDO_PERMISSION:
            return ""

        command = f"sudo smartctl -H {self.name}"
        try:
            result_code, output_stdout, output_stderr = do_command(command)

            if result_code != 0:
                logger.warning(f"Error running smartctl: {output_stderr}")
                return ""

            smart_info = output_stdout
            return smart_info

        except Exception as e:
            logger.warning(f"An error occurred: {e}")
            return ""
