import json
import threading
from time import sleep as time_sleep
from typing import List, Tuple

import requests

from config.settings import (
    GROUP_CENTER_PASSWORD,
    GROUP_CENTER_URL,
    SERVER_NAME,
    SERVER_NAME_SHORT,
    USE_GROUP_CENTER,
)
from monitor.info.enum import TaskEvent
from monitor.info.group_center_task_info import TaskInfoForGroupCenter
from utils.logs import get_logger
from utils.security import get_md5_hash

logger = get_logger()


def get_url(target: str):
    if GROUP_CENTER_URL.endswith("/"):
        if target.startswith("/"):
            target = target[1:]
    else:
        if not target.startswith("/"):
            target = "/" + target

    return GROUP_CENTER_URL + target


access_key = ""

public_part: dict = {
    "serverName": SERVER_NAME,
    "serverNameEng": SERVER_NAME_SHORT,
}


def hand_shake_to_center(
        username: str,
        password: str
) -> bool:
    logger.info("[Group Center] Auth Handshake Start")
    url = get_url(target="/auth/client/auth")
    try:
        logger.info(f"[Group Center] Auth To: {url}")
        password_display = "*" * len(password)
        password_encoded = get_md5_hash(password)
        logger.info(f"[Group Center] Auth userName:{username} password:{password_display}")
        response = requests.get(
            url=url,
            params={
                "userName": username,
                "password": password_encoded
            },
            timeout=10
        )

        if response.status_code != 200:
            logger.error(f"[Group Center] Auth Failed: {response.text}")
            return False

        response_dict: dict = json.loads(response.text)
        if (not (
                "isAuthenticated" in response_dict.keys() and
                response_dict["isAuthenticated"]
        )):
            logger.error("[Group Center] Not authorized")
            return False
        global access_key
        access_key = response_dict["accessKey"]
        logger.info(f"[Group Center] Auth Handshake Success: {access_key}")

    except Exception as e:
        logger.error(f"[Group Center] Auth Handshake Failed: {e}")
        return False
    logger.info("[Group Center] Auth Handshake Finished.")


def send_dict_to_center(data: dict, target: str) -> bool:
    url = get_url(target=target)
    try:
        response = requests.post(url, json=data, timeout=10)

        response_dict: dict = json.loads(response.text)

        if (not (
                "isAuthenticated" in response_dict.keys() and
                response_dict["isAuthenticated"]
        )):
            logger.error("[Group Center] Not authorized")
            hand_shake_to_center(
                username=SERVER_NAME_SHORT,
                password=GROUP_CENTER_PASSWORD
            )
            return False

        if (not (
                "isSucceed" in response_dict.keys() and
                response_dict["isSucceed"]
        )):
            logger.error(f"[Group Center] Send {target} Failed: {response.text}")
            return False

        logger.info(f"[Group Center] Send {target} Success")
        return True
    except Exception as e:
        logger.error(f"[Group Center] Send {target} Failed: {e}")
        return False


def gpu_monitor_start():
    logger.info("[Group Center] Gpu Monitor Start")


task_list: List[Tuple[dict, str]] = []


class GroupCenterWorkThread(threading.Thread):
    need_work = True

    def __init__(self):
        super(GroupCenterWorkThread, self).__init__()

    def run(self):
        global task_list, access_key

        while self.need_work:
            if access_key == "":
                hand_shake_to_center(
                    username=SERVER_NAME_SHORT,
                    password=GROUP_CENTER_PASSWORD
                )
            if len(task_list) > 0:
                data, target = task_list[0]
                final_data = {
                    **public_part,
                    **data,
                    "accessKey": access_key
                }
                if send_dict_to_center(
                        data=final_data,
                        target=target
                ):
                    task_list.pop(0)
                else:
                    # 出错多休息一会儿~
                    time_sleep(20)

            time_sleep(10)


work_thread = None


def add_task_to_center(data: dict, target: str):
    if not USE_GROUP_CENTER:
        return

    global task_list, work_thread
    task_list.append((data, target))

    if work_thread is None:
        work_thread = GroupCenterWorkThread()
        work_thread.start()


def gpu_task_message(process_obj, task_event: TaskEvent):
    from monitor.GPU.gpu_process import GPUProcessInfo
    process_obj: GPUProcessInfo = process_obj

    logger.info(
        f"[Group Center] Task "
        f"User:{process_obj.user.name_cn} "
        f"PID:{process_obj.pid} "
        f"Event:{task_event.value}"
    )

    data_dict: dict = {
        "messageType": task_event.value,
    }

    taskInfoForGroupCenterGpuObj = TaskInfoForGroupCenter(process_obj)

    data_dict.update(taskInfoForGroupCenterGpuObj.__dict__)

    add_task_to_center(data_dict, "/api/client/gpu_task/info")
