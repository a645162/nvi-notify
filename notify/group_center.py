from typing import List
import threading
import requests
from time import sleep as time_sleep

from config.settings import (
    GROUP_CENTER_URL
)

from utils.logs import get_logger

logger = get_logger()


def get_url(target: str):
    return (GROUP_CENTER_URL + target).replace("//", "/")


def hand_shake_to_center(
        username: str,
        password: str
):
    pass


def send_dict_to_center(data: dict, target: str) -> bool:
    url = get_url(target=target)
    try:
        requests.post(url, json=data, timeout=10)
        logger.info(f"[Group Center] Send {target} Success")
        return True
    except Exception as e:
        logger.error(f"[Group Center] Send {target} Failed: {e}")
        return False


def gpu_monitor_start():
    logger.info("[Group Center] Gpu Monitor Start")


task_list: List[(dict, str)] = []


class GroupCenterWorkThread(threading.Thread):
    need_work = True

    def __init__(self):
        super(GroupCenterWorkThread, self).__init__()

    def run(self):
        global task_list

        while self.need_work:
            if len(task_list) > 0:
                data, target = task_list[0]
                if send_dict_to_center(data=data, target=target):
                    task_list.pop(0)
                else:
                    # 出错多休息一会儿~
                    time_sleep(60)

            time_sleep(10)


work_thread: GroupCenterWorkThread


def add_task_to_center(data: dict, target: str):
    global task_list, work_thread
    task_list.append((data, target))

    if work_thread is None:
        work_thread = GroupCenterWorkThread()
        work_thread.start()


def gpu_task_message(process_obj, task_status: str):
    from monitor.GPU.gpu_process import GPUProcessInfo
    process_obj: GPUProcessInfo = process_obj

    logger.info(
        f"[Group Center] Task "
        f"User:{process_obj.user_name} "
        f"PID:{process_obj.pid} "
        f"Status:{task_status}"
    )

    data_dict: dict = {
        # 任务唯一标识符
        "taskId": process_obj.task_task_id,

        "messageType": task_status,

        # 任务类型
        "taskType": "gpu",
        # 任务状态
        "taskStatus": process_obj.state,
        # 用户
        "taskUser": process_obj.user_name,
        # 进程PID
        "taskPid": process_obj.pid,
        "taskMainMemory": process_obj.task_main_memory_mb,

        # GPU 信息
        "taskGpuId": process_obj.gpu_id,
        "taskGpuName": process_obj.gpu_name,

        "taskGpuMemoryMb": process_obj.task_main_memory_mb,
        "taskGpuMemoryHuman": process_obj.task_gpu_memory_human,

        "taskGpuMemoryMaxMb": process_obj.task_gpu_memory_max,

        # 运行时间
        "startTime": process_obj.start_time,

        "taskRunningTime": process_obj.running_time_human,
        "taskRunningTimeInSeconds": process_obj.running_time_in_seconds
    }

    add_task_to_center(data_dict, "/api/client/gpu_task/info")
