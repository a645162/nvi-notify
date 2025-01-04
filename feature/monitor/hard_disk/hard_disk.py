import humanfriendly

from config.settings import (
    HARD_DISK_HIGH_PERCENTAGE_THRESHOLD,
    HARD_DISK_LOW_FREE_GB_THRESHOLD,
    SUDO_PERMISSION,
)
from feature.monitor.monitor_enum import MonitorEnum
from feature.utils import cat_info, do_command, get_logger

logger = get_logger()


class DiskPurpose(MonitorEnum):
    SYSTEM = "system"
    DATA = "data"
    SYSTEM_CN = "系统盘"
    DATA_CN = "数据盘"


class DiskType(MonitorEnum):
    SSD = "ssd"
    HDD = "hdd"
    SSD_CN = "固态硬盘"
    HDD_CN = "机械硬盘"


class HardDisk:
    total_str: str
    used_str: str
    free_str: str

    def __init__(self, name: str, mount_point: str) -> None:
        """
        Args:
            name (str): disk name. such as 'sda1', 'nvme0n1'.
            mount_point (str): mount point. such as '/', '/home'.
        """
        self._name: str = ""
        self._mount_point: str = ""
        self._type: DiskType = None
        self._purpose: DiskPurpose = None
        self._purpose_cn: DiskPurpose = None

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

        self.name: str = name
        self.mount_point: str = mount_point

    def update_info(self, info: list[str]) -> None:
        """更新硬盘使用信息

        Args:
            info (list[str]): 从 df 命令解析出的硬盘信息列表
                [文件系统, 总大小, 已用大小, 可用大小, 使用百分比, 挂载点]
        """
        if len(info) < 5:
            logger.warning(f"Invalid disk info: {info}")
            return

        self.total_str, self.used_str, self.free_str, self.percentage_used_str = info[1:]

    @property
    def name(self) -> str:
        return self._name

    @name.setter 
    def name(self, value: str) -> None:
        if (
            "nvme" not in value
            and cat_info(f"/sys/block/{value}/queue/rotational").strip() == "1"
        ):
            self._type = DiskType.HDD
        else:
            self._type = DiskType.SSD
        self._name = value

    @property
    def free_str(self) -> str:
        return self._free_str

    @free_str.setter
    def free_str(self, value: str) -> None:
        self.free_bytes = humanfriendly.parse_size(value, binary=True)
        self._free_str = value

    @property
    def free_bytes(self) -> float:
        return self._free_bytes

    @free_bytes.setter
    def free_bytes(self, cur_free_bytes: float) -> None:
        self._low_free_bytes_trigger = cur_free_bytes < self._low_free_bytes_threshold
        self._free_bytes = cur_free_bytes

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
        self._high_percentage_used_trigger = (
                cur_percentage_used > self._high_percentage_used_threshold
        )
        self._percentage_used_int = cur_percentage_used

    @property
    def mount_point(self) -> str:
        return self._mount_point

    @mount_point.setter
    def mount_point(self, value: str) -> None:
        if value == "/":
            self._purpose = DiskPurpose.SYSTEM
            self._purpose_cn = DiskPurpose.SYSTEM_CN
            self._high_percentage_used_threshold = 85
            self._low_free_bytes_threshold = humanfriendly.parse_size(
                "50GB", binary=True
            )
        else:
            self._purpose = DiskPurpose.DATA
            self._purpose_cn = DiskPurpose.DATA_CN
            self._high_percentage_used_threshold = HARD_DISK_HIGH_PERCENTAGE_THRESHOLD
            self._low_free_bytes_threshold = humanfriendly.parse_size(
                f"{HARD_DISK_LOW_FREE_GB_THRESHOLD}GB", binary=True
            )
        self._mount_point = value

    @property
    def size_warning_trigger(self) -> bool:
        if self._purpose == DiskPurpose.SYSTEM:
            return self._low_free_bytes_trigger
        elif self._purpose == DiskPurpose.DATA:
            return self._low_free_bytes_trigger and self._high_percentage_used_trigger

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
            "/mnt/datasets": "~/datasets"
        }
        return linked_dict[mount_point]

    def get_smart_info(self) -> str:
        if not SUDO_PERMISSION:
            return ""

        command = f"sudo smartctl -H {self.name}"
        try:
            result_code, output_stdout, output_stderr = do_command(command)

            if result_code.returncode != 0:
                logger.warning(f"Error running smartctl: {output_stderr}")
                return

            smart_info = output_stdout
            return smart_info

        except Exception as e:
            logger.warning(f"An error occurred: {e}")
            return ""
