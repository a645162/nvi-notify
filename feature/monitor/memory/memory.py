import psutil

from feature.global_variable.system import global_system_info
from feature.monitor.utils import Converter


class MemoryInfo:
    def __init__(self) -> None:
        memory_physic = Memory.get_memory_info()
        memory_swap = Memory.get_swap_memory_info()
        global_system_info.update(
            {
                "memoryPhysicTotalMb": Converter.convert_bytes_to_mb(
                    memory_physic.total
                ),
                "memorySwapTotalMb": Converter.convert_bytes_to_mb(memory_swap.total),
            }
        )

    @staticmethod
    def update():
        memory_physic = Memory.get_memory_info()
        memory_swap = Memory.get_swap_memory_info()
        global_system_info.update(
            {
                "memoryPhysicUsedMb": Converter.convert_bytes_to_mb(memory_physic.used),
                # "memoryPhysicFreeMb": Converter.convert_bytes_to_mb(memory_physic.free),
                "memorySwapUsedMb": Converter.convert_bytes_to_mb(memory_swap.used),
                # "memorySwapFreeMb": Converter.convert_bytes_to_mb(memory_swap.free),
            }
        )


class Memory:
    @staticmethod
    def get_memory_info():
        return psutil.virtual_memory()

    @staticmethod
    def get_swap_memory_info():
        return psutil.swap_memory()
