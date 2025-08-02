from typing import TYPE_CHECKING

import psutil

from feature.group_center import data_manager
from feature.monitor.utils import Converter

if TYPE_CHECKING:
    from psutil._common import sswap
    from psutil._pslinux import svmem

data_manager_ins = data_manager.get_data_manager()

class MemoryInfo:
    def __init__(self) -> None:
        memory_physic = Memory.get_memory_info()
        memory_swap = Memory.get_swap_memory_info()
        data_manager_ins.system_info.update(
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
        data_manager_ins.system_info.update(
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
