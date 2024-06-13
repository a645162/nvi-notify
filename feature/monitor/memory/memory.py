import psutil

from feature.global_variable.system import global_system_info
from feature.monitor.utils import Converter


class MemoryInfo:
    def update():
        memory_physic = Memory.get_memory_info()
        memory_swap = Memory.get_swap_memory_info()

        global_system_info["memoryPhysicTotalMb"] = Converter.convert_bytes_to_mb(
            memory_physic.total
        )
        global_system_info["memoryPhysicUsedMb"] = Converter.convert_bytes_to_mb(
            memory_physic.used
        )
        # global_system_info["memoryPhysicFreeMb"] = Converter.convert_bytes_to_mb(
        #     memory_physic.free
        # )

        global_system_info["memorySwapTotalMb"] = Converter.convert_bytes_to_mb(
            memory_swap.total
        )
        global_system_info["memorySwapUsedMb"] = Converter.convert_bytes_to_mb(
            memory_swap.used
        )
        # global_system_info["memorySwapFreeMb"] = Converter.convert_bytes_to_mb(
        #     memory_swap.free
        # )


class Memory:
    @staticmethod
    def get_memory_info():
        return psutil.virtual_memory()

    @staticmethod
    def get_swap_memory_info():
        return psutil.swap_memory()
