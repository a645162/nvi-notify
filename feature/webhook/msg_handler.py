from group_center.core.feature import custom_client_message

from feature.config import settings, user_info
from feature.monitor import enum
from feature.utils import logs
from feature.webhook import webhook

logger = logs.get_logger()


class MessageHandler:
    @staticmethod
    def handle_normal_text(msg: str) -> str:
        """
        处理普通文本消息函数
        :param msg: 消息内容
        :return: 处理后的消息内容
        """
        if settings.SERVER_DOMAIN is None:
            msg += f"📈http://{settings.IPv4}\n"
            # msg += f"http://[{settings.IPv6}]\n"
        else:
            msg += f"📈http://{settings.SERVER_DOMAIN}\n"

        msg += f"⏰{settings.EnvironmentManager.now_time_str()}"
        return msg

    @staticmethod
    def handle_warning_text(msg: str) -> str:
        """
        处理警告文本消息函数
        :param msg: 消息内容
        :return: 处理后的消息内容
        """
        msg += f"http://{settings.IPv4}\n"
        msg += f"http://[{settings.IPv6}]\n"
        msg += f"⏰{settings.EnvironmentManager.now_time_str()}"
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
        warning_message = f"⚠️⚠️{settings.SERVER_NAME}{keyword}！⚠️⚠️\n"
        msg = cls.handle_warning_text(warning_message)

        webhook.Webhook.send_warning_msg_to_webhook_all_time(msg, enum.MsgType.WARNING)

    @classmethod
    def enqueue_cpu_temperature_warning_msg(
        cls, cpu_id: int, cpu_temperature: float
    ) -> None:
        """
        CPU温度警告消息函数
        """
        warning_message = (
            f"🤒🤒{settings.SERVER_NAME}的CPU:{cpu_id}温度已达{cpu_temperature}°C\n"
        )
        msg = cls.handle_warning_text(warning_message)

        webhook.Webhook.send_warning_msg_to_webhook_all_time(msg, enum.MsgType.WARNING)

    @classmethod
    def enqueue_cpu_aver_temperature_warning_msg(
        cls, cpu_id: int, cpu_aver_temperature: float
    ) -> None:
        """
        CPU平均温度警告消息函数
        """
        warning_message = f"🤒🤒{settings.SERVER_NAME}的CPU:{cpu_id}近5分钟平均温度已达{cpu_aver_temperature:.1f}°C\n"
        msg = cls.handle_warning_text(warning_message)

        webhook.Webhook.send_warning_msg_to_webhook_all_time(msg, enum.MsgType.WARNING)

    @classmethod
    def enqueue_hard_disk_warning_msg(cls, disk_info: str) -> None:
        """
        向群聊中发送硬盘高占用警告消息
        """
        warning_message = f"⚠️【硬盘可用空间不足】⚠️\n{disk_info}"
        msg = cls.handle_normal_text(warning_message)

        # Send to wework directly
        webhook.Webhook.enqueue_msg_to_webhook(
            msg,
            enum.MsgType.NORMAL,
            mention_everyone=True,
            enable_webhook_name=enum.AllWebhookName.WEWORK,
        )

        # Send to lark by Group Center
        custom_client_message.machine_message_directly(
            server_name=settings.SERVER_NAME,
            server_name_eng=settings.SERVER_NAME_SHORT,
            content=msg,
            at="all",
        )

    @classmethod
    def enqueue_hard_disk_warning_msg_to_user(
        cls, disk_info: str, dir_info: tuple[str, str], user: user_info.UserInfo
    ) -> None:
        """
        通过飞书app向各用户发送硬盘高占用警告消息
        """
        if user.lark_info["mention_id"] == [""]:
            logger.warning(f"用户{user.name_cn}没有配置Lark通知ID，无法发送消息。")
            return

        dir_name, dir_size = dir_info
        if dir_name == "/home":
            last_str = (
                "可能是 Conda 环境较多，请及时清理不需要使用的 Conda 环境。\n"
                "查看当前用户下所有环境的命令： conda env list \n"
                "删除某个 Conda 环境的命令： conda env remove -n 环境名 --all \n"
            )
        else:
            last_str = "请及时清理不需要的文件。\n"
        warning_message = (
            f"⚠️【硬盘可用空间不足】⚠️\n"
            f"{disk_info}\n"
            f"⚠️用户{user.name_cn}的个人目录[{dir_name}]占用容量为{dir_size}，{last_str}"
        )

        msg = cls.handle_normal_text(warning_message)

        # Send to lark app directly
        # webhook.Webhook.enqueue_warning_msg_for_user_to_webhook(msg, user)

        # Send to lark app by Group Center
        custom_client_message.machine_user_message_directly(
            user_name=user.name_cn, content=msg
        )
