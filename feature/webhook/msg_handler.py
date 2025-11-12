# -*- coding: utf-8 -*-
import time

from group_center.core.feature.custom_client_message import (
    machine_message_directly,
    machine_user_message_directly,
)
from group_center.core.feature.machine_message import new_message_enqueue

from config.settings import (
    SERVER_DOMAIN,
    SERVER_NAME,
    SERVER_NAME_SHORT,
    USE_GROUP_CENTER,
    EnvironmentManager,
    IPv4,
    IPv6,
)
from config.user_info import UserInfo
from feature.monitor.monitor_enum import AllWebhookName, MsgType
from feature.utils.logs import get_logger
from feature.webhook.webhook import Webhook

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

        msg += f"⏰{EnvironmentManager.now_time_str()}"
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
        msg += f"⏰{EnvironmentManager.now_time_str()}"
        return msg

    @classmethod
    def enqueue_except_warning_msg(cls, except_type: str) -> None:
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

        Webhook.send_warning_msg_to_webhook_all_time(msg, MsgType.WARNING)

    @classmethod
    def enqueue_cpu_temperature_warning_msg(cls, cpu_id: int, cpu_temperature: float):
        """
        CPU温度警告消息函数
        """
        warning_message = (
            f"🤒🤒{SERVER_NAME}的CPU:{cpu_id}温度已达{cpu_temperature}°C\n"
        )
        msg = cls.handle_warning_text(warning_message)

        # 发送到GroupCenter报警接口
        if USE_GROUP_CENTER:
            alarm_data = {
                "title": f"🤒 CPU温度报警 - {SERVER_NAME}",
                "content": f"CPU {cpu_id} 温度已达到 {cpu_temperature}°C，请及时处理！",
                "source": SERVER_NAME,
                "urgent": True,
                "timestamp": int(time.time() * 1000),  # Java兼容的时间戳（毫秒）
            }
            new_message_enqueue(alarm_data, "/api/client/alarm")

        Webhook.send_warning_msg_to_webhook_all_time(msg, MsgType.WARNING)

    @classmethod
    def enqueue_cpu_aver_temperature_warning_msg(
        cls, cpu_id: int, cpu_aver_temperature: float
    ):
        """
        CPU平均温度警告消息函数
        """
        warning_message = f"🤒🤒{SERVER_NAME}的CPU:{cpu_id}近5分钟平均温度已达{cpu_aver_temperature:.1f}°C\n"
        msg = cls.handle_warning_text(warning_message)

        # 发送到GroupCenter报警接口
        if USE_GROUP_CENTER:
            alarm_data = {
                "title": f"🤒 CPU平均温度报警 - {SERVER_NAME}",
                "content": f"CPU {cpu_id} 近5分钟平均温度已达到 {cpu_aver_temperature:.1f}°C，请及时处理！",
                "source": SERVER_NAME,
                "urgent": True,
                "timestamp": int(time.time() * 1000),  # Java兼容的时间戳（毫秒）
            }
            new_message_enqueue(alarm_data, "/api/client/alarm")

        Webhook.send_warning_msg_to_webhook_all_time(msg, MsgType.WARNING)

    @classmethod
    def enqueue_hard_disk_warning_msg(cls, disk_info: str, rank_message: str = ""):
        """
        向群聊中发送硬盘高占用警告消息
        """
        warning_message = f"⚠️【硬盘可用空间不足】⚠️\n{disk_info}"
        if rank_message:
            warning_message += f"\n{rank_message}"
        msg = cls.handle_normal_text(warning_message)

        # 发送到GroupCenter报警接口
        if USE_GROUP_CENTER:
            alarm_data = {
                "title": f"⚠️ 硬盘容量报警 - {SERVER_NAME}",
                "content": f"{disk_info}\n{rank_message}" if rank_message else disk_info,
                "source": SERVER_NAME,
                "urgent": False,
                "timestamp": int(time.time() * 1000),  # Java兼容的时间戳（毫秒）
            }
            new_message_enqueue(alarm_data, "/api/client/alarm")

        # Send to wework directly
        Webhook.enqueue_msg_to_webhook(
            msg,
            MsgType.NORMAL,
            mention_everyone=True,
            enable_webhook_name=AllWebhookName.WEWORK,
        )

        # Send to lark by Group Center
        machine_message_directly(
            server_name=SERVER_NAME,
            server_name_eng=SERVER_NAME_SHORT,
            content=msg,
            at="all",
        )

    @classmethod
    def enqueue_hard_disk_warning_msg_to_user(
        cls, disk_info: str, dir_info: tuple[str, str], user: UserInfo
    ):
        """
        通过飞书app向各用户发送硬盘高占用警告消息
        """
        if user.lark_info["mention_id"] == [""]:
            logger.warning(f"用户{user.name_cn}没有配置Lark通知ID，无法发送消息。")
            return

        dir_name, dir_size = dir_info
        if dir_name == "/home":
            last_str = ("可能是 Conda 环境较多，请及时清理不需要使用的 Conda 环境。\n"
                        "查看当前用户下所有环境的命令： conda env list \n"
                        "删除某个 Conda 环境的命令： conda env remove -n 环境名 --all \n")
        else:
            last_str = "请及时清理不需要的文件。\n"
        warning_message = (
            f"⚠️【硬盘可用空间不足】⚠️\n"
            f"{disk_info}\n"
            f"⚠️用户{user.name_cn}的个人目录[{dir_name}]占用容量为{dir_size}，{last_str}"
        )

        msg = cls.handle_normal_text(warning_message)

        # 不再发送到GroupCenter报警接口，只发送总的报警
        # Send to lark app directly
        # Webhook.enqueue_warning_msg_for_user_to_webhook(msg, user)

        # Send to lark app by Group Center
        machine_user_message_directly(user_name=user.name_cn, content=msg)
