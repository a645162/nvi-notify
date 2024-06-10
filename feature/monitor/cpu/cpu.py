import psutil

from utils.utils import do_command


class CPUInfo:
    @staticmethod
    def get_cpu_num() -> int:
        command = "cat /proc/cpuinfo | grep 'physical id' | sort -u | wc -l"
        result = do_command(command)

        if result[0] == 0:
            return int(result[1].strip())
        else:
            return 0

    @staticmethod
    def get_cpu_physics_core_num():
        return psutil.cpu_count(logical=False)

    @staticmethod
    def get_cpu_logic_core_num():
        return psutil.cpu_count(logical=True)

    @staticmethod
    def get_cpu_percent(interval=0):
        if interval == 0:
            return psutil.cpu_percent()
        return psutil.cpu_percent(interval=interval)