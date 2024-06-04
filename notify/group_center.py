import requests
from utils.logs import get_logger

logger = get_logger()


def gpu_monitor_start():
    logger.info("[Group Center] Gpu Monitor Start")


def gpu_task_message(process_obj, task_status: str):
    from monitor.GPU.gpu_process import GPUProcessInfo
    process_obj: GPUProcessInfo = process_obj

    logger.info(f"gpu_task_message pid:{process_obj.pid}")
