from config.settings import get_settings
from feature.monitor.monitor_enum import MonitorEnum

settings = get_settings()


class DiskPurpose(MonitorEnum):
    SYSTEM = "system"
    DATA = "data"
    SYSTEM_CN = "系统盘"
    DATA_CN = "数据盘"


class DiskType(MonitorEnum):
    NVME = "nvme"
    HDD = "hdd"
    NVME_CN = "固态硬盘"
    HDD_CN = "机械硬盘"


class HardDisk:
    def __init__(self, mount_point: str) -> None:
        self._low_free_space_trigger = False
        self._high_percentage_used_trigger = False

        self._name = ""
        self._total = ""
        self._used = ""
        self._free_str = ""
        self._percentage_used_str = ""
        self._mount_point = ""
        self._free_GB_float = 9999.9
        self._percentage_used_int = 0
        self._type = None
        self._purpose = None
        self._purpose_cn = None
        self._high_percentage_used_threshold = 0
        self._low_free_space_threshold = 0

        self.mount_point = mount_point

    def update_info(self, info: list):
        self.name = info[0]
        self.total = info[1]
        self.used = info[2]
        self.free_str = info[3]
        self.percentage_used_str = info[4]
        # self.mount_point = info[5]

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: DiskType) -> None:
        if "nvme" in value:
            self.type = DiskType.NVME
        else:
            self.type = DiskType.HDD
        self._name = value

    @property
    def total(self) -> str:
        return self._total

    @total.setter
    def total(self, value: str) -> None:
        self._total = value

    @property
    def used(self) -> str:
        return self._used

    @used.setter
    def used(self, value: str) -> None:
        self._used = value

    @property
    def free_str(self) -> str:
        return self._free_str

    @free_str.setter
    def free_str(self, value: str) -> None:
        if "T" in value:
            self.free_GB_float = float(value.replace("T", "")) * 1024
        elif "G" in value:
            self.free_GB_float = float(value.replace("G", ""))
        elif "M" in value:
            self.free_GB_float = float(value.replace("M", "")) / 1024
        else:
            self.free_GB_float = 0.0
        self._free_str = value

    @property
    def free_GB_float(self) -> float:
        return self._free_GB_float

    @free_GB_float.setter
    def free_GB_float(self, cur_free_GB: float) -> None:
        self.low_free_space_trigger = (
            cur_free_GB < self.low_free_space_threshold
        ) and (cur_free_GB < self._free_GB_float)
        self._free_GB_float = cur_free_GB

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
        self.high_percentage_used_trigger = (
            cur_percentage_used > self.high_percentage_used_threshold
        )
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
            self.low_free_space_threshold = 50
        else:
            self.purpose = DiskPurpose.DATA
            self.purpose_cn = DiskPurpose.DATA_CN
            self.high_percentage_used_threshold = (
                settings.HARD_DISK_HIGH_PERCENTAGE_THRESHOLD
            )
            self.low_free_space_threshold = settings.HARD_DISK_LOW_FREE_GB_THRESHOLD
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
    def type(self) -> str:
        return self._type

    @type.setter
    def type(self, value: str) -> None:
        self._type = value

    @property
    def high_percentage_used_threshold(self) -> int:
        return self._high_percentage_used_threshold

    @high_percentage_used_threshold.setter
    def high_percentage_used_threshold(self, value: int) -> None:
        self._high_percentage_used_threshold = value

    @property
    def low_free_space_threshold(self) -> int:
        return self._low_free_space_threshold

    @low_free_space_threshold.setter
    def low_free_space_threshold(self, value: int) -> None:
        self._low_free_space_threshold = value

    @property
    def high_percentage_used_trigger(self) -> bool:
        return self._high_percentage_used_trigger

    @high_percentage_used_trigger.setter
    def high_percentage_used_trigger(self, value: bool) -> None:
        self._high_percentage_used_trigger = value

    @property
    def low_free_space_trigger(self) -> bool:
        return self._low_free_space_trigger

    @low_free_space_trigger.setter
    def low_free_space_trigger(self, value: bool) -> None:
        self._low_free_space_trigger = value

    @property
    def size_warning_trigger(self) -> bool:
        if self.purpose == DiskPurpose.SYSTEM:
            return self.low_free_space_trigger
        elif self.purpose == DiskPurpose.DATA:
            return self.low_free_space_trigger and self.high_percentage_used_trigger

    def disk_info(self):
        return (
            f"{self.purpose_cn}(挂载点为{self.mount_point})"
            f"剩余可用容量为{self.free_str}，总容量为{self.total}，"
            f"占用率为{self.percentage_used_str}\n"
        )
