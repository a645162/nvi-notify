import requests
from utils.logs import get_logger

logger = get_logger()


def gpu_monitor_start():
    logger.info("[Group Center] Gpu Monitor Start")


def gpu_task_message(process_obj, task_status: str):
    from monitor.GPU.gpu_process import GPUProcessInfo
    process_obj: GPUProcessInfo = process_obj

    logger.info(
        f"[Group Center] Task "
        f"User:{process_obj.user_name} "
        f"PID:{process_obj.pid} "
        f"Status:{task_status}"
    )

    if task_status == "create":
        pass
    elif task_status == "start":
        pass
    else:
        logger.error("[Group Center] 'task_status' ERROR!")
