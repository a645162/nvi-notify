from group_center.core.feature.machine_message import new_message_enqueue

from config.settings import USE_GROUP_CENTER
from feature.group_center. \
    datatype.group_center_task_info import TaskInfoForGroupCenter
from feature.monitor.monitor_enum import TaskEvent
from feature.utils.logs import get_logger

logger = get_logger()


def gpu_monitor_start(gpu_id: int):
    if not USE_GROUP_CENTER:
        return

    logger.info(f"[Group Center] Gpu{gpu_id} Monitor Start")


def gpu_task_message(process_obj, task_event: TaskEvent):
    if not USE_GROUP_CENTER:
        return

    from feature.monitor.gpu.gpu_process import GPUProcessInfo

    process_obj: GPUProcessInfo = process_obj

    logger.info(
        f"[Group Center] Task "
        f"User:{process_obj.user.name_cn} "
        f"PID:{process_obj.pid} "
        f"Event:{task_event.value}"
    )

    data_dict = {
        "messageType": task_event.value,
    }

    task_info_obj = TaskInfoForGroupCenter(process_obj)

    data_dict.update(task_info_obj.__dict__)

    new_message_enqueue(data_dict, "/api/client/gpu_task/info")
