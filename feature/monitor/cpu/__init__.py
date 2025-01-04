"""CPU监控模块

该模块包含CPU监控相关的类和函数，用于监控CPU的温度和使用情况。
"""

from .cpu import CPU
from .monitor import CPUMonitor, start_cpu_monitor_all

__all__ = ["CPU", "CPUMonitor", "start_cpu_monitor_all"]
