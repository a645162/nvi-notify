from __future__ import annotations

from typing import TYPE_CHECKING

from group_center.core.feature import machine_message

from nvi_notify.config import settings
from nvi_notify.entity import task_info
from nvi_notify.monitor import enums
from nvi_notify.utils import logs

if TYPE_CHECKING:
    from nvi_notify.entity import process

logger = logs.get_logger()


def gpu_monitor_start(gpu_id: int) -> None:
    if not settings.USE_GROUP_CENTER:
        return

    logger.info(f"[Group Center] Gpu{gpu_id} Monitor Start")


def gpu_task_message(
    process_obj: process.GPUProcessInfo, task_event: enums.TaskEvent
) -> None:
    if not settings.USE_GROUP_CENTER:
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
        "serverName": settings.SERVER_NAME,
        "serverNameEng": settings.SERVER_NAME_SHORT,
    }

    task_info_obj = task_info.TaskInfoForRemote(process_obj)

    data_dict.update(task_info_obj.__dict__)

    machine_message.new_message_enqueue(data_dict, "/api/client/gpu_task/info")
