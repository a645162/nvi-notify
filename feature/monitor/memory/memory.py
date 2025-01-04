from typing import Dict

import psutil

from feature.global_variable.system import global_system_info
from feature.utils import Converter, get_logger

logger = get_logger()


class Memory:
    """内存信息管理类，负责收集和更新系统内存信息"""

    def __init__(self) -> None:
        """初始化内存信息，设置总内存和交换内存大小"""
        self._update_total_memory_info()

    @staticmethod
    def update() -> None:
        """更新当前内存使用情况"""
        try:
            memory_physic = Memory.get_memory_info()
            memory_swap = Memory.get_swap_memory_info()

            update_data: Dict[str] = {
                "memoryPhysicUsedMb": Converter.convert_bytes_to_mb(memory_physic.used),
                # "memoryPhysicFreeMb": Converter.convert_bytes_to_mb(memory_physic.free),
                "memorySwapUsedMb": Converter.convert_bytes_to_mb(memory_swap.used),
                # "memorySwapFreeMb": Converter.convert_bytes_to_mb(memory_swap.free),
            }

            global_system_info.update(update_data)
            logger.debug("内存信息更新成功")

        except psutil.Error as e:
            logger.error(f"获取内存信息失败: {str(e)}")
        except Exception as e:
            logger.error(f"获取内存信息失败: {str(e)}")

    @staticmethod
    def _update_total_memory_info() -> None:
        """更新总内存信息"""
        try:
            memory_physic = Memory.get_memory_info()
            memory_swap = Memory.get_swap_memory_info()

            update_data: Dict[str] = {
                "memoryPhysicTotalMb": Converter.convert_bytes_to_mb(memory_physic.total),
                "memorySwapTotalMb": Converter.convert_bytes_to_mb(memory_swap.total),
            }

            global_system_info.update(update_data)
            logger.debug("总内存信息更新成功")

        except psutil.Error as e:
            logger.error(f"获取总内存信息失败: {str(e)}")
        except Exception as e:
            logger.error(f"更新总内存信息失败: {str(e)}")

    @staticmethod
    def get_memory_info() -> psutil._common.svmem:
        """获取物理内存信息

        Returns:
            psutil._common.svmem: 物理内存信息对象

        Raises:
            psutil.Error: 如果获取内存信息失败
        """
        try:
            memory_info = psutil.virtual_memory()
            logger.debug(f"获取物理内存信息成功: {memory_info}")
            return memory_info
        except psutil.Error as e:
            logger.error(f"获取物理内存信息失败: {str(e)}")
            raise

    @staticmethod
    def get_swap_memory_info() -> psutil._common.sswap:
        """获取交换内存信息

        Returns:
            psutil._common.sswap: 交换内存信息对象

        Raises:
            psutil.Error: 如果获取交换内存信息失败
        """
        try:
            swap_info = psutil.swap_memory()
            logger.debug(f"获取交换内存信息成功: {swap_info}")
            return swap_info
        except psutil.Error as e:
            logger.error(f"获取交换内存信息失败: {str(e)}")
            raise
