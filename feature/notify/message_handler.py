# -*- coding: utf-8 -*-
from config.settings import SERVER_DOMAIN, SERVER_NAME, IPv4, IPv6, now_time_str
from config.user.user_info import UserInfo
from feature.monitor.monitor_enum import AllWebhookName, MsgType
from feature.notify.webhook import Webhook
from feature.utils.logs import get_logger

logger = get_logger()


class MessageHandler:
    @staticmethod
    def handle_normal_text(msg: str) -> str:
        """
        处理普通文本消息函数
        :param msg: 消息内容
        :return: 处理后的消息内容
        """
        if SERVER_DOMAIN is None:
            msg += f"📈http://{IPv4}\n"
            # msg += f"http://[{IPv6}]\n"
        else:
            msg += f"📈http://{SERVER_DOMAIN}\n"

        msg += f"⏰{now_time_str()}"
        return msg

    @staticmethod
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

    @classmethod
    def enqueue_except_warning_msg(cls, except_type: str):
        """
        异常警告消息函数
        """
        assert except_type in ["process", "cpu"]
        if except_type == "process":
            keyword = "获取进程失败"
        elif except_type == "cpu":
            keyword = "获取CPU温度失败"
        else:
            keyword = ""
        warning_message = f"⚠️⚠️{SERVER_NAME}{keyword}！⚠️⚠️\n"
        msg = cls.handle_warning_text(warning_message)

        Webhook.enqueue_msg_to_webhook(msg, MsgType.WARNING)

    @classmethod
    def enqueue_cpu_temperature_warning_msg(cls, cpu_id: int, cpu_temperature: float):
        """
        CPU温度警告消息函数
        """
        warning_message = (
            f"🤒🤒{SERVER_NAME}的CPU:{cpu_id}温度已达{cpu_temperature}°C\n"
        )
        msg = cls.handle_warning_text(warning_message)

        Webhook.enqueue_msg_to_webhook(msg, MsgType.WARNING)

    @classmethod
    def enqueue_hard_disk_size_warning_msg(cls, disk_info: str):
        """
        发送硬盘高占用警告消息函数
        """
        warning_message = f"⚠️【硬盘可用空间不足】⚠️\n{disk_info}"
        msg = cls.handle_normal_text(warning_message)

        Webhook.enqueue_msg_to_webhook(
            msg,
            MsgType.NORMAL,
            mention_everyone=True,
            enable_webhook_name=AllWebhookName.ALL,
        )

    @classmethod
    def enqueue_hard_disk_size_warning_msg_to_user(
        cls, disk_info: str, dir_path, dir_size: str, user: UserInfo
    ):
        """
        向用户发送硬盘高占用警告消息函数
        """
        if user.lark_info["mention_id"] == [""]:
            logger.warnning(f"用户{user.name_cn}没有配置Lark通知ID，无法发送消息。")
            return
        warning_message = (
            f"⚠️【硬盘可用空间不足】⚠️\n"
            f"{disk_info}\n"
            f"⚠️用户{user.name_cn}的个人目录[{dir_path}]占用容量为{dir_size}。\n"
        )
        msg = cls.handle_normal_text(warning_message)

        Webhook.enqueue_warning_msg_for_user_to_webhook(msg, user)
