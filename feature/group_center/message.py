from __future__ import annotations

from typing import TYPE_CHECKING

from group_center.core.feature.machine_message import new_message_enqueue

from config.settings import SERVER_NAME, SERVER_NAME_SHORT, USE_GROUP_CENTER
from feature.group_center.datatype.task_info import TaskInfoForGroupCenter
from feature.monitor.monitor_enum import TaskEvent
from feature.utils.logs import get_logger

if TYPE_CHECKING:
    from feature.monitor.gpu.gpu_process import GPUProcessInfo

logger = get_logger()


def gpu_monitor_start(gpu_id: int) -> None:
    if not USE_GROUP_CENTER:
        return

    logger.info(f"[Group Center] Gpu{gpu_id} Monitor Start")


def gpu_task_message(process_obj: GPUProcessInfo, task_event: TaskEvent) -> None:
    if not USE_GROUP_CENTER:
        return

    user_name_cn = getattr(process_obj.user, "name_cn", "Unknown")

    logger.info(
        f"[Group Center] Task "
        f"User:{user_name_cn} "
        f"PID:{process_obj.pid} "
        f"Event:{task_event.value}"
    )

    data_dict = {
        "messageType": task_event.value,
        "serverName": SERVER_NAME,
        "serverNameEng": SERVER_NAME_SHORT,
    }

    task_info_obj = TaskInfoForGroupCenter(process_obj)

    data_dict.update(task_info_obj.__dict__)

    new_message_enqueue(data_dict, "/api/client/gpu_task/info")
