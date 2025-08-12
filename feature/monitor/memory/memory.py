from __future__ import annotations

from typing import TYPE_CHECKING

import psutil

from feature.group_center.data_manager import DataManager
from feature.monitor.utils import Converter

if TYPE_CHECKING:
    from psutil._common import sswap
    from psutil._pslinux import svmem


class MemoryInfo:
    def __init__(self) -> None:
        memory_physic = Memory.get_memory_info()
        memory_swap = Memory.get_swap_memory_info()
        DataManager().system_info.update(
            {
                "memoryPhysicTotalMb": Converter.convert_bytes_to_mb(
                    memory_physic.total
                ),
                "memorySwapTotalMb": Converter.convert_bytes_to_mb(memory_swap.total),
            }
        )

    @staticmethod
    def update() -> None:
        memory_physic = Memory.get_memory_info()
        memory_swap = Memory.get_swap_memory_info()
        DataManager().system_info.update(
            {
                "memoryPhysicUsedMb": Converter.convert_bytes_to_mb(memory_physic.used),
                # "memoryPhysicFreeMb": Converter.convert_bytes_to_mb(memory_physic.free),
                "memorySwapUsedMb": Converter.convert_bytes_to_mb(memory_swap.used),
                # "memorySwapFreeMb": Converter.convert_bytes_to_mb(memory_swap.free),
            }
        )


class Memory:
    @staticmethod
    def get_memory_info() -> svmem:
        return psutil.virtual_memory()

    @staticmethod
    def get_swap_memory_info() -> sswap:
        return psutil.swap_memory()
