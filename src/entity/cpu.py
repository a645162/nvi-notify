from collections import deque

import psutil

from src.config import settings
from src.utils import common_utils


class CPU:
    def __init__(self, idx: int) -> None:
        self.idx: int = idx
        self.high_temperature_trigger: bool = False
        self.high_aver_temperature_trigger: bool = False

        self.temperature_samples = deque(maxlen=15)

        self._temperature: float = 0.0
        self._average_temperature = 0.0

    @property
    def temperature(self) -> float:
        return self._temperature

    @temperature.setter
    def temperature(self, new_temperature: float) -> None:
        self.temperature_samples.append(new_temperature)
        self.high_temperature_trigger = new_temperature > 95
        self._temperature = new_temperature

    @property
    def average_temperature(self) -> float:
        return self._average_temperature

    @average_temperature.setter
    def average_temperature(self, new_aver_temperature: float) -> None:
        self.high_aver_temperature_trigger = (
            new_aver_temperature > settings.CPU_HIGH_TEMPERATURE_THRESHOLD
        )
        self._average_temperature = new_aver_temperature

    @staticmethod
    def get_cpu_num() -> int:
        command = "cat /proc/cpuinfo | grep 'physical id' | sort -u | wc -l"
        code, ret, err = common_utils.get_terminal_output(command)

        if code == 0:
            return int(ret.strip())
        else:
            return 0

    @staticmethod
    def get_cpu_physics_core_num() -> int:
        ret = psutil.cpu_count(logical=False)
        return ret if ret else -1

    @staticmethod
    def get_cpu_logic_core_num() -> int:
        ret = psutil.cpu_count(logical=True)
        return ret if ret else -1

    @staticmethod
    def get_cpu_percent(interval: int = 0) -> float:
        if interval == 0:
            return psutil.cpu_percent()
        return psutil.cpu_percent(interval=interval)
