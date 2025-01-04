"""内存监控模块

该模块提供了系统内存信息的监控功能，包括：
- 物理内存使用情况
- 交换内存使用情况
- 内存信息的实时更新
"""

from .memory import Memory

__all__ = ["Memory"]
