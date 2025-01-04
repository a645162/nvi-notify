from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional

import psutil

from config.settings import CPU_HIGH_TEMPERATURE_THRESHOLD
from feature.utils import do_command, get_logger

logger = get_logger()


@dataclass
class CPU:
    """CPU信息管理类，负责收集和监控CPU信息"""

    idx: int
    _temperature: float = 0.0
    _average_temperature: float = 0.0
    _high_temperature_trigger: bool = False
    _high_aver_temperature_trigger: bool = False
    temperature_samples: Deque[float] = field(default_factory=lambda: deque(maxlen=15))

    @property
    def temperature(self) -> float:
        """获取当前CPU温度"""
        return self._temperature

    @temperature.setter
    def temperature(self, new_temperature: float) -> None:
        """设置当前CPU温度并检查是否触发高温警告

        Args:
            new_temperature: 新的温度值
        """
        self.temperature_samples.append(new_temperature)
        self._high_temperature_trigger = new_temperature > 95
        self._temperature = new_temperature
        logger.debug(f"CPU {self.idx} 温度更新为: {new_temperature}°C")

    @property
    def average_temperature(self) -> float:
        """获取CPU平均温度"""
        return self._average_temperature

    @average_temperature.setter
    def average_temperature(self, new_aver_temperature: float) -> None:
        """设置CPU平均温度并检查是否触发高温警告

        Args:
            new_aver_temperature: 新的平均温度值
        """
        self._high_aver_temperature_trigger = (
            new_aver_temperature > CPU_HIGH_TEMPERATURE_THRESHOLD
        )
        self._average_temperature = new_aver_temperature
        logger.debug(f"CPU {self.idx} 平均温度更新为: {new_aver_temperature}°C")

    @staticmethod
    def get_cpu_num() -> int:
        """获取物理CPU数量

        Returns:
            int: 物理CPU数量，如果获取失败返回0
        """
        command = "cat /proc/cpuinfo | grep 'physical id' | sort -u | wc -l"
        result_code, result, result_err = do_command(command)

        if result_code == 0:
            cpu_num = int(result.strip())
            logger.debug(f"获取物理CPU数量成功: {cpu_num}")
            return cpu_num
        else:
            logger.error(f"获取物理CPU数量失败: {result_err}")
            return 0

    @staticmethod
    def get_cpu_physics_core_num() -> Optional[int]:
        """获取物理核心数量

        Returns:
            Optional[int]: 物理核心数量，如果获取失败返回None
        """
        try:
            core_num = psutil.cpu_count(logical=False)
            logger.debug(f"获取物理核心数量成功: {core_num}")
            return core_num
        except Exception as e:
            logger.error(f"获取物理核心数量失败: {str(e)}")
            return None

    @staticmethod
    def get_cpu_logic_core_num() -> Optional[int]:
        """获取逻辑核心数量

        Returns:
            Optional[int]: 逻辑核心数量，如果获取失败返回None
        """
        try:
            core_num = psutil.cpu_count(logical=True)
            logger.debug(f"获取逻辑核心数量成功: {core_num}")
            return core_num
        except Exception as e:
            logger.error(f"获取逻辑核心数量失败: {str(e)}")
            return None

    @staticmethod
    def get_cpu_percent(interval: float = 0) -> float:
        """获取CPU使用率

        Args:
            interval: 采样间隔时间（秒）

        Returns:
            float: CPU使用率百分比
        """
        try:
            usage = psutil.cpu_percent(interval)
            logger.debug(f"获取CPU使用率成功: {usage}%")
            return usage
        except Exception as e:
            logger.error(f"获取CPU使用率失败: {str(e)}")
            return 0.0
