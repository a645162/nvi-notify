import psutil

from feature.monitor.utils import Converter


class Memory:
    @staticmethod
    def convert_mem_to_str(mem_bytes: int) -> str:
        mem_gb = Converter.convert_bytes_to_gb(mem_bytes)
        return f"{mem_gb:.1f}"

    @staticmethod
    def get_memory_info():
        return psutil.virtual_memory()

    @staticmethod
    def get_swap_memory_info():
        return psutil.swap_memory()
