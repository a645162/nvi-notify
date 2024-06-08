# -*- coding: utf-8 -*-

import os
from pathlib import Path

from config.settings import (
    NUM_GPU,
    SERVER_DOMAIN,
    SERVER_NAME,
    WEBHOOK_DELAY_SEND_SECONDS,
    IPv4,
    IPv6,
    get_emoji,
    get_now_time,
)
from config.user import UserInfo
from feature.monitor.info.program_enum import AllWebhookName, MsgType, TaskEvent
from feature.monitor.info.webhook_task_info import TaskInfoForWebHook
from feature.notify.webhook import send_text
from utils.logs import get_logger

logger = get_logger()


def send_gpu_monitor_start_msg(gpu_id: int, all_process_info: dict):
    """
    启动GPU监控函数
    :param gpu_id: GPU ID
    :param all_process_info: 所有进程信息字典
    """
    gpu_name = f"[GPU:{gpu_id}]" if NUM_GPU > 1 else "GPU"

    gpu_status = None
    send_start_info = False

    all_tasks_msg = ""

    for process in all_process_info.values():
        if (
            process.running_time_in_seconds > WEBHOOK_DELAY_SEND_SECONDS
            and not process.is_debug
        ):
            if process.is_multi_gpu and process.local_rank != 0:
                continue

            send_start_info = True
            gpu_status = process.gpu_status
            all_tasks_msg = "".join(process.gpu_all_tasks_msg.values())
            break

    if send_start_info:
        handle_normal_text(
            f"{gpu_name}监控启动\n"
            f"{get_emoji('呲牙') * len(all_process_info)}"
            f"{gpu_name}上正在运行{len(all_process_info)}个任务：\n"
            f"{all_tasks_msg}\n"
            f"🌀{gpu_name}核心占用: {gpu_status.utl}%\n"
            f"🌀{gpu_name}显存占用: {gpu_status.mem_usage}/{gpu_status.mem_total} "
            f"({gpu_status.mem_percent}%)，{gpu_status.mem_free}空闲\n",
        )


def send_gpu_task_message(process_info: dict, task_event: str):
    """
    发送GPU任务消息函数
    :param process_info: 进程信息字典
    :param task_event: 任务状态
    """
    task = TaskInfoForWebHook(process_info, task_event)
    gpu_name = task.gpu_name
    gpu_name_header = gpu_name + '\n' if NUM_GPU > 1 else ''
    if not task.is_debug:
        multi_gpu_msg = task.multi_gpu_msg
        if multi_gpu_msg == "-1":  # 非第一个使用的GPU不发送消息
            return

        if task_event == TaskEvent.CREATE:
            msg_header = (
                f"{gpu_name_header}🚀"
                f"{task.user.name_cn}的"
                f"{multi_gpu_msg}"
                f"({task.screen_name}{task.project_name}-{task.python_file})启动"
                "\n"
            )
        elif task_event == TaskEvent.FINISH:
            msg_header = (
                f"{gpu_name_header}☑️"
                f"{task.user.name_cn}的"
                f"{multi_gpu_msg}"
                f"({task.screen_name}{task.project_name}-{task.python_file})完成，"
                f"用时{task.running_time_human}，"
                f"最大显存{task.task_gpu_memory_max_human}"
                "\n"
            )
        emoji_num_task = get_emoji("呲牙") * (task.num_task)
        gpu_task_status_info_msg = (
            f"{emoji_num_task}{gpu_name}上正在运行{task.num_task}个任务：\n"
        )
        if task.num_task == 0:
            gpu_task_status_info_msg = f"{gpu_name}当前无任务\n"

        handle_normal_text(
            msg=msg_header
            + task.gpu_status_msg
            + gpu_task_status_info_msg
            + task.all_task_msg,
            user=task.user if task_event == TaskEvent.FINISH else None,
        )


def log_task_info(process_info: dict, task_event: str):
    """
    任务日志函数
    :param process_info: 进程信息字典
    :task_event: 任务类型, `create` or `finish`
    """
    if task_event is None:
        raise ValueError("task_event is None")

    logfile_dir_path = Path("./log")
    if not os.path.exists(logfile_dir_path):
        os.makedirs(logfile_dir_path)

    task = TaskInfoForWebHook(process_info, task_event)

    with open(logfile_dir_path / "user_task.log", "a") as log_writer:
        if task_event == TaskEvent.CREATE:
            output_log = (
                f"{task.gpu_name}"
                f" {task.user.name_cn} "
                f"create new {'debug ' if task.is_debug else ''}"
                f"task: {task.pid}"
            )
        elif task_event == TaskEvent.FINISH:
            output_log = (
                f"{task.gpu_name}"
                f" finish {task.user.name_cn}'s {'debug ' if task.is_debug else ''}"
                f"task: {task.pid}，用时{task.running_time_human}"
            )
        log_writer.write(f"[{get_now_time()}]+{output_log} + \n")
        logger.info(output_log)
        print(output_log)


def handle_normal_text(msg: str, user: UserInfo = None):
    """
    处理普通文本消息函数
    :param msg: 消息内容
    :param mentioned_id: 提及的用户ID
    :param mentioned_mobile: 提及的用户手机号码
    """
    if SERVER_DOMAIN is None:
        msg += f"📈http://{IPv4}\n"
        # msg += f"http://[{IPv6}]\n"
    else:
        msg += f"📈http://{SERVER_DOMAIN}\n"

    msg += f"⏰{get_now_time()}"
    send_text(msg, MsgType.NORMAL, user, AllWebhookName.ALL)


def handle_warning_text(msg: str) -> str:
    """
    处理警告文本消息函数
    :param msg: 消息内容
    :return: 处理后的消息内容
    """
    msg += f"http://{IPv4}\n"
    msg += f"http://[{IPv6}]\n"
    msg += f"⏰{get_now_time()}"
    return msg


def send_process_except_warning_msg():
    """
    发送进程异常警告消息函数
    """
    warning_message = f"⚠️⚠️{SERVER_NAME}获取进程失败！⚠️⚠️\n"
    send_text(msg=handle_warning_text(warning_message), msg_type=MsgType.WARNING)


def send_cpu_except_warning_msg(cpu_id: int):
    """
    发送CPU异常警告消息函数
    """
    warning_message = f"⚠️⚠️{SERVER_NAME}获取CPU:{cpu_id}温度失败！⚠️⚠️\n"
    send_text(msg=handle_warning_text(warning_message), msg_type=MsgType.WARNING)


def send_cpu_temperature_warning_msg(cpu_id: int, cpu_temperature: float):
    """
    发送CPU温度异常警告消息函数
    """
    warning_message = f"🤒🤒{SERVER_NAME}的CPU:{cpu_id}温度已达{cpu_temperature}°C\n"
    send_text(msg=handle_warning_text(warning_message), msg_type=MsgType.WARNING)

def send_hard_disk_high_occupancy_warning_msg(
    name: str, mountpoint: str, total_GB: float, free_GB: float, percentage: float
):
    """
    发送硬盘高占用警告消息函数
    """
    hard_disk_name_for_msg = {"system": "系统盘", "data": "数据盘"}

    warning_message = (
        f"⚠️【硬盘可用空间不足】⚠️\n"
        f"{hard_disk_name_for_msg.get(name, 'Unknown')}(挂载点为{mountpoint})"
        f"剩余可用容量为{free_GB:.2f}GB，总容量为{total_GB:.2f}GB，占用率为{percentage:.2f}%\n"
    )

    handle_normal_text(msg=warning_message)
