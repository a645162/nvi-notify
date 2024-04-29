# -*- coding: utf-8 -*-

from typing import List

from monitor.GPU.python_process import PythonGPUProcess

from utils.logs import get_logger

logger = get_logger()

logger.info("Global Variable:global_gpu Initializing...")

"""
gpu_info:
包括 GPU名称、TDP

gpu_usage:
包含 当前功率、温度(摄氏度)、核心使用率、显存使用率、显存使用量、显存总量

gpu_task为一个列表
包括 用户名、是否为调试模式、工程名、py文件名、显存占用、运行时间
"""

global_gpu_info: List[dict] = []
global_gpu_usage: List[dict] = []
global_gpu_task: List[List[PythonGPUProcess]] = []


# For Debug Use
# global_gpu_usage.append({})
# global_gpu_task.append([])


def get_gpu_count():
    if len(global_gpu_usage) != len(global_gpu_task):
        raise ValueError(
            "global_gpu_usage and global_gpu_task should have the same length."
        )
    return len(global_gpu_task)
