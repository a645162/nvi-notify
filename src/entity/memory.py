from dataclasses import dataclass
from typing import TYPE_CHECKING

import psutil

from src.api import data_manager
from src.utils.data_utils import Converter

if TYPE_CHECKING:
    from psutil._common import sswap
    from psutil._pslinux import svmem

data_manager_ins = data_manager.get_data_manager()


@dataclass(frozen=True)
class MemoryInfo:
    """内存信息数据类"""

    total_physical_mb: float
    total_swap_mb: float
    used_physical_mb: float
    used_swap_mb: float

    @classmethod
    def collect(cls) -> "MemoryInfo":
        """收集当前系统内存信息"""
        physical = MemoryInfo.get_physicalmemory_info()
        swap = MemoryInfo.get_swap_memory_info()

        return cls(
            total_physical_mb=Converter.convert_bytes_to_mb(physical.total),
            total_swap_mb=Converter.convert_bytes_to_mb(swap.total),
            used_physical_mb=Converter.convert_bytes_to_mb(physical.used),
            used_swap_mb=Converter.convert_bytes_to_mb(swap.used),
        )

    @staticmethod
    def get_physicalmemory_info() -> svmem:
        """获取物理内存信息"""
        return psutil.virtual_memory()

    @staticmethod
    def get_swap_memory_info() -> sswap:
        """获取交换内存信息"""
        return psutil.swap_memory()


class Memory:
    """系统内存信息管理类"""

    def __init__(self) -> None:
        """初始化内存信息，记录总内存大小"""
        memory = MemoryInfo.collect()
        data_manager_ins.system_info.update(
            {
                "memoryPhysicTotalMb": memory.total_physical_mb,
                "memorySwapTotalMb": memory.total_swap_mb,
            }
        )

    @staticmethod
    def update() -> None:
        memory = MemoryInfo.collect()
        data_manager_ins.system_info.update(
            {
                "memoryPhysicUsedMb": memory.used_physical_mb,
                # "memoryPhysicFreeMb": memory.free_physic_mb,
                "memorySwapUsedMb": memory.used_swap_mb,
                # "memorySwapFreeMb": memory.free_swap_mb,
            }
        )
