# -*- coding: utf-8 -*-

from feature.utils.logs import get_logger

logger = get_logger()

logger.info("Global Variable:global_system Initializing...")

"""
global_system_info为一个Hashmap
包括:
物理内存、分页内存(总量/使用量)
"""

global_system_info: dict = {
    "memoryPhysicTotalMb": 0,
    "memoryPhysicUsedMb": 0,

    "memorySwapTotalMb": 0,
    "memorySwapUsedMb": 0,
}
