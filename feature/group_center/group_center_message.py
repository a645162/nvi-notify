import json
import threading
import time
from typing import Tuple

import requests

from config.settings import USE_GROUP_CENTER
from feature.group_center.group_center import (
    access_key,
    group_center_get_url,
    group_center_login,
    group_center_public_part,
)
from feature.group_center.group_center_task_info import TaskInfoForGroupCenter
from feature.monitor.monitor_enum import TaskEvent
from feature.utils.logs import get_logger

logger = get_logger()


def send_dict_to_center(data: dict, target: str) -> bool:
    url = group_center_get_url(target_api=target)
    try:
        response = requests.post(url, json=data, timeout=10)

        response_dict: dict = json.loads(response.text)

        if not (
                "isAuthenticated" in response_dict.keys()
                and response_dict["isAuthenticated"]
        ):
            logger.error("[Group Center] Not authorized")
            group_center_login()
            return False

        if not ("isSucceed" in response_dict.keys() and response_dict["isSucceed"]):
            logger.error(f"[Group Center] Send {target} Failed: {response.text}")
            return False

        logger.info(f"[Group Center] Send {target} Success")
        return True
    except Exception as e:
        logger.error(f"[Group Center] Send {target} Failed: {e}")
        return False


task_list: list[Tuple[dict, str]] = []


class GroupCenterWorkThread(threading.Thread):
    need_work = True

    def __init__(self):
        super(GroupCenterWorkThread, self).__init__()

    def run(self):
        global task_list

        while self.need_work:
            if access_key == "":
                group_center_login()
            if len(task_list) > 0:
                data, target = task_list[0]
                final_data = {
                    **group_center_public_part,
                    **data,
                    "accessKey": access_key,
                }
                if send_dict_to_center(data=final_data, target=target):
                    task_list.pop(0)
                else:
                    # 出错多休息一会儿~
                    time.sleep(20)

            time.sleep(10)


work_thread = None


def add_task_to_center(data: dict, target: str):
    if not USE_GROUP_CENTER:
        return

    global task_list, work_thread
    task_list.append((data, target))

    if work_thread is None:
        work_thread = GroupCenterWorkThread()
        work_thread.start()


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

    add_task_to_center(data_dict, "/api/client/gpu_task/info")
