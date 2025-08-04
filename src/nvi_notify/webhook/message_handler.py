from group_center.core.feature import custom_client_message

from nvi_notify.config import settings, user_info
from nvi_notify.monitor import enums as monitor_enums
from nvi_notify.utils import logs
from nvi_notify.webhook import (
    enums as webhook_enums,
    webhook,
)

logger = logs.get_logger()


def wrap_host_url_info(
    msg: str, enable_ipv6: bool = False, enable_domain: bool = True
) -> str:
    """处理主机信息函数"""
    if settings.SERVER_DOMAIN is not None and enable_domain:
        msg = f"{msg}📈http://{settings.SERVER_DOMAIN}\n"
    else:
        msg = f"{msg}📈http://{settings.IPv4}\n"

        if settings.IPv6 is not None and enable_ipv6:
            msg = f"{msg}http://[{settings.IPv6}]\n"

    return msg


def wrap_now_time_info(msg: str) -> str:
    """ "处理当前时间信息函数"""
    return f"{msg}⏰{settings.EnvironmentManager.now_time_str()}"


def wrap_normal_level_msg(msg: str) -> str:
    """
    处理普通文本消息函数
    :param msg: 消息内容
    :return: 处理后的消息内容
    """
    msg = wrap_host_url_info(msg)
    msg = wrap_now_time_info(msg)
    return msg


def wrap_warning_level_msg(msg: str) -> str:
    """
    处理警告文本消息函数
    :param msg: 消息内容
    :return: 处理后的消息内容
    """
    msg = wrap_host_url_info(msg, enable_ipv6=True, enable_domain=False)
    msg = wrap_now_time_info(msg)
    return msg


def enqueue_except_warning_msg(except_type: str) -> None:
    """
    异常警告消息函数
    """
    assert except_type in ["process", "cpu"]
    error_title = ""
    if except_type == "process":
        error_title = "获取进程失败"
    elif except_type == "cpu":
        error_title = "获取CPU温度失败"

    warning_message = f"⚠️⚠️{settings.SERVER_NAME}{error_title}！⚠️⚠️\n"
    msg = wrap_warning_level_msg(warning_message)

    webhook.Webhook.send_warning_msg_to_webhook_all_time(
        msg, monitor_enums.MsgType.WARNING
    )


def enqueue_cpu_temperature_warning_msg(cpu_id: int, temperature: float) -> None:
    """CPU温度警告消息函数"""
    warning_message = (
        f"🤒🤒{settings.SERVER_NAME}的CPU:{cpu_id}温度已达{temperature}°C\n"
    )
    msg = wrap_warning_level_msg(warning_message)

    webhook.Webhook.send_warning_msg_to_webhook_all_time(
        msg, monitor_enums.MsgType.WARNING
    )


def enqueue_cpu_aver_temperature_warning_msg(
    cpu_id: int, aver_temperature: float
) -> None:
    """CPU平均温度警告消息函数."""
    warning_message = f"🤒🤒{settings.SERVER_NAME}的CPU:{cpu_id}近5分钟平均温度已达{aver_temperature:.1f}°C\n"
    msg = wrap_warning_level_msg(warning_message)

    webhook.Webhook.send_warning_msg_to_webhook_all_time(
        msg, monitor_enums.MsgType.WARNING
    )


def enqueue_hard_disk_warning_msg(disk_info: str) -> None:
    """向群聊中发送硬盘高占用警告消息."""
    warning_message = f"⚠️【硬盘可用空间不足】⚠️\n{disk_info}"
    msg = wrap_normal_level_msg(warning_message)

    # Send to wework directly
    webhook.Webhook.enqueue_msg_to_webhook(
        msg,
        monitor_enums.MsgType.NORMAL,
        mention_everyone=True,
        enable_name=webhook_enums.AllWebhookName.WEWORK,
    )

    # Send to lark by Group Center
    custom_client_message.machine_message_directly(
        server_name=settings.SERVER_NAME,
        server_name_eng=settings.SERVER_NAME_SHORT,
        content=msg,
        at="all",
    )


def enqueue_hard_disk_warning_msg_to_user(
    disk_info: str, dir_info: tuple[str, str], user: user_info.UserInfo
) -> None:
    """通过飞书app向各用户发送硬盘高占用警告消息."""
    if user.lark_info["mention_id"] == [""]:
        logger.warning(f"用户{user.name_cn}没有配置Lark通知ID，无法发送消息。")
        return

    dir_name, dir_size = dir_info
    if dir_name == "/home":
        tip_str = (
            "可能是 Conda 环境较多，请及时清理不需要使用的 Conda 环境。\n"
            "查看当前用户下所有环境的命令： conda env list \n"
            "删除某个 Conda 环境的命令： conda env remove -n 环境名 --all \n"
        )
    else:
        tip_str = "请及时清理不需要的文件。\n"
    warning_message = (
        f"⚠️【硬盘可用空间不足】⚠️\n"
        f"{disk_info}\n"
        f"⚠️用户{user.name_cn}的个人目录[{dir_name}]占用容量为{dir_size}，{tip_str}"
    )

    msg = wrap_normal_level_msg(warning_message)

    # Send to lark app directly
    # webhook.Webhook.enqueue_warning_msg_for_user_to_webhook(msg, user)

    # Send to lark app by Group Center
    custom_client_message.machine_user_message_directly(
        user_name=user.name_cn, content=msg
    )
