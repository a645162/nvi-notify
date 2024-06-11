# -*- coding: utf-8 -*-

import os
from pathlib import Path

from config.settings import (
    SERVER_DOMAIN,
    SERVER_NAME,
    IPv4,
    IPv6,
    now_time_str,
)
from config.user.user_info import UserInfo
from feature.monitor.gpu.task.for_webhook import TaskInfoForWebHook
from feature.monitor.monitor_enum import AllWebhookName, MsgType, TaskEvent
from feature.notify.webhook import send_text
from utils.logs import get_logger

logger = get_logger()


def log_task_info(process_info: dict, task_event: TaskEvent):
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
        log_writer.write(f"[{now_time_str()}]+{output_log} + \n")
        logger.info(output_log)
        # print(output_log)


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

    msg += f"⏰{now_time_str()}"
    send_text(msg, MsgType.NORMAL, user, AllWebhookName.ALL)


def handle_warning_text(msg: str) -> str:
    """
    处理警告文本消息函数
    :param msg: 消息内容
    :return: 处理后的消息内容
    """
    msg += f"http://{IPv4}\n"
    msg += f"http://[{IPv6}]\n"
    msg += f"⏰{now_time_str()}"
    return msg


def send_process_except_warning_msg():
    """
    发送进程异常警告消息函数
    """
    warning_message = f"⚠️⚠️{SERVER_NAME}获取进程失败！⚠️⚠️\n"
    send_text(msg=handle_warning_text(warning_message), msg_type=MsgType.WARNING)


def send_cpu_except_warning_msg():
    """
    发送CPU异常警告消息函数
    """
    warning_message = f"⚠️⚠️{SERVER_NAME}获取CPU温度失败！⚠️⚠️\n"
    send_text(msg=handle_warning_text(warning_message), msg_type=MsgType.WARNING)


def send_cpu_temperature_warning_msg(cpu_id: int, cpu_temperature: float):
    """
    发送CPU温度异常警告消息函数
    """
    warning_message = f"🤒🤒{SERVER_NAME}的CPU:{cpu_id}温度已达{cpu_temperature}°C\n"
    send_text(msg=handle_warning_text(warning_message), msg_type=MsgType.WARNING)


def send_hard_disk_size_warning_msg(disk_info: str):
    """
    发送硬盘高占用警告消息函数
    """

    warning_message = f"⚠️【硬盘可用空间不足】⚠️\n{disk_info}"

    handle_normal_text(msg=warning_message)
