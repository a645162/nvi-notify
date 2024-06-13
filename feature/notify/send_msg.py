# -*- coding: utf-8 -*-
from config.settings import SERVER_DOMAIN, SERVER_NAME, IPv4, IPv6, now_time_str
from config.user.user_info import UserInfo
from feature.monitor.monitor_enum import AllWebhookName, MsgType
from feature.notify.webhook import Webhook


def handle_normal_text(msg: str):
    """
    处理普通文本消息函数
    :param msg: 消息内容
    :param user: 提及的用户
    :return: 处理后的消息内容
    """
    if SERVER_DOMAIN is None:
        msg += f"📈http://{IPv4}\n"
        # msg += f"http://[{IPv6}]\n"
    else:
        msg += f"📈http://{SERVER_DOMAIN}\n"

    msg += f"⏰{now_time_str()}"
    return msg


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
    Webhook.enqueue_msg_to_webhook(
        handle_warning_text(warning_message), MsgType.WARNING
    )


def send_cpu_except_warning_msg():
    """
    发送CPU异常警告消息函数
    """
    warning_message = f"⚠️⚠️{SERVER_NAME}获取CPU温度失败！⚠️⚠️\n"
    Webhook.enqueue_msg_to_webhook(
        handle_warning_text(warning_message), MsgType.WARNING
    )


def send_cpu_temperature_warning_msg(cpu_id: int, cpu_temperature: float):
    """
    发送CPU温度异常警告消息函数
    """
    warning_message = f"🤒🤒{SERVER_NAME}的CPU:{cpu_id}温度已达{cpu_temperature}°C\n"
    Webhook.enqueue_msg_to_webhook(
        handle_warning_text(warning_message), MsgType.WARNING
    )


def send_hard_disk_size_warning_msg(disk_info: str):
    """
    发送硬盘高占用警告消息函数
    """

    warning_message = f"⚠️【硬盘可用空间不足】⚠️\n{disk_info}"
    msg = handle_normal_text(warning_message)

    Webhook.enqueue_msg_to_webhook(
        msg,
        MsgType.NORMAL,
        mention_everyone=True,
        enable_webhook_name=AllWebhookName.ALL,
    )


def send_hard_disk_size_warning_msg_to_user(
    disk_info: str, dir_path, dir_size_info: str, user: UserInfo
):
    """
    向用户发送硬盘高占用警告消息函数
    """

    warning_message = (
        f"⚠️【硬盘可用空间不足】⚠️\n"
        f"{disk_info}\n"
        f"⚠️用户{user.name_cn}的个人目录[{dir_path}]占用容量为{dir_size_info}。\n"
    )
    msg = handle_normal_text(warning_message)
    if user is None or user.lark_info["mention_id"] == [""]:
        return

    Webhook.enqueue_warning_msg_for_user_to_webhook(msg, user)
