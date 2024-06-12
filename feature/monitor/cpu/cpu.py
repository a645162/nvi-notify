import psutil

from config.settings import CPU_HIGH_TEMPERATURE_THRESHOLD
from utils.utils import do_command


class CPUInfo:
    @staticmethod
    def get_cpu_num() -> int:
        command = "cat /proc/cpuinfo | grep 'physical id' | sort -u | wc -l"
        result_code, result, result_err = do_command(command)

        if result_code == 0:
            return int(result.strip())
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


class CPU:
    def __init__(self, idx: int) -> None:
        self._idx: int = idx
        self._temperature: float = 0.0
        self._high_temperature_trigger: bool = False

    @property
    def idx(self) -> int:
        return self._idx

    @idx.setter
    def idx(self, value: int) -> None:
        self._idx = value

    @property
    def temperature(self) -> float:
        return self._temperature

    @temperature.setter
    def temperature(self, new_temperature: float) -> None:
        self.high_temperature_trigger = (
            new_temperature > CPU_HIGH_TEMPERATURE_THRESHOLD > self._temperature
        )

        self._temperature = new_temperature

    @property
    def high_temperature_trigger(self) -> bool:
        return self._high_temperature_trigger

    @high_temperature_trigger.setter
    def high_temperature_trigger(self, value: bool) -> None:
        self._high_temperature_trigger = value
