import datetime
from pathlib import Path

from nvi_notify.config import user_config_parser, user_info
from nvi_notify.utils import common_utils, logs

logger = logs.get_logger()
default_datetime_time = object()


def is_webhook_quiet_period(
    start_time: datetime.time | object = default_datetime_time,
    end_time: datetime.time | object = default_datetime_time,
) -> bool:
    if isinstance(start_time, object) or isinstance(end_time, object):
        from nvi_notify.config import settings  # noqa: PLC0415

        start_time = settings.WEBHOOK_SLEEP_TIME_START
        end_time = settings.WEBHOOK_SLEEP_TIME_END

    if is_now_in_time_span(start_time, end_time):
        return True
    else:
        return False


def is_now_in_time_span(
    start_time: datetime.time = datetime.time(11, 0),
    end_time: datetime.time = datetime.time(7, 30),
) -> bool:
    current_time = datetime.datetime.now().time()

    if start_time <= end_time:
        return start_time <= current_time <= end_time
    else:
        return start_time <= current_time or current_time <= end_time


def get_seconds_until_webhook_wake_up(
    end_time: datetime.time | object = default_datetime_time,
) -> float:
    if isinstance(end_time, object):
        from nvi_notify.config import settings  # noqa: PLC0415

        end_time = settings.WEBHOOK_SLEEP_TIME_END

    current_datetime = datetime.datetime.now()
    current_time = current_datetime.time()
    end_datetime = datetime.datetime.combine(current_datetime.date(), end_time)

    if end_time <= current_time:
        end_datetime += datetime.timedelta(days=1)

    time_to_sleep = (end_datetime - current_datetime).total_seconds()

    return time_to_sleep  # 返回整数秒数


def get_users() -> dict[str, user_info.UserInfo]:
    from nvi_notify.config import settings  # noqa: PLC0415

    users: dict[str, user_info.UserInfo] = {}
    parser = user_config_parser.UserConfigParser()

    user_from_local = settings.EnvironmentManager.get_bool(
        "USER_FROM_LOCAL_FILES", True
    )

    if user_from_local:
        users_dict = parser.get_user_info_by_yaml(Path.cwd() / "config" / "users")
        logger.info(f"User count from local: {len(users_dict)}")
        users.update(users_dict)

    user_from_remote = (
        settings.USE_GROUP_CENTER
        and settings.EnvironmentManager.get_bool("USER_FROM_GROUP_CENTER", False)
    )

    if user_from_remote:
        users_dict = parser.get_user_config_from_remote()
        logger.info(f"User count from remote (Group Center): {len(users_dict)}")
        users.update(users_dict)

    logger.info(f"Final user count: {len(users)}")

    return users


def set_iptables(port: int) -> None:
    cmd_list = [
        f"sudo iptables -I INPUT -p tcp --dport {port} -j ACCEPT",
        f"sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port {port}",
        f"sudo ip6tables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port {port}",
    ]
    for cmd in cmd_list:
        try:
            common_utils.get_terminal_output(cmd)
        except Exception as e:
            logger.warning(f"Set iptables error: {e} when executing {cmd}")

    logger.info("Set iptables success!")
