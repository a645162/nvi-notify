import datetime
from pathlib import Path

from feature.config import user_info
from feature.utils import common_utils, logs

logger = logs.get_logger()
default_datetime_time = object()


def is_webhook_sleep_time(
    start_time: datetime.time | object = default_datetime_time,
    end_time: datetime.time | object = default_datetime_time,
) -> bool:
    if isinstance(start_time, object) or isinstance(end_time, object):
        from feature.config import settings  # noqa: PLC0415

        start_time = settings.WEBHOOK_SLEEP_TIME_START
        end_time = settings.WEBHOOK_SLEEP_TIME_END

    if is_within_time_range(start_time, end_time):
        return True
    else:
        return False


def is_within_time_range(
    start_time: datetime.time = datetime.time(11, 0),
    end_time: datetime.time = datetime.time(7, 30),
) -> bool:
    current_time = datetime.datetime.now().time()

    if start_time <= end_time:
        return start_time <= current_time <= end_time
    else:
        return start_time <= current_time or current_time <= end_time


def get_seconds_to_sleep_until_end(
    end_time: datetime.time | object = default_datetime_time,
) -> float:
    if isinstance(end_time, object):
        from feature.config import settings  # noqa: PLC0415

        end_time = settings.WEBHOOK_SLEEP_TIME_END

    current_datetime = datetime.datetime.now()
    current_time = current_datetime.time()
    end_datetime = datetime.datetime.combine(current_datetime.date(), end_time)

    if end_time <= current_time:
        end_datetime += datetime.timedelta(days=1)

    time_to_sleep = (end_datetime - current_datetime).total_seconds()

    return time_to_sleep  # 返回整数秒数


def get_users() -> dict[str, user_info.UserInfo]:
    from feature.config import settings  # noqa: PLC0415

    users_obj_dict: dict[str, user_info.UserInfo] = {}
    user_config_parser = user_info.UserConfigParser()
    user_from_group_center = (
        settings.USE_GROUP_CENTER
        and settings.EnvironmentManager.get_bool("USER_FROM_GROUP_CENTER", False)
    )
    user_from_local_files = settings.EnvironmentManager.get_bool(
        "USER_FROM_LOCAL_FILES", True
    )

    if user_from_local_files:
        user_list_from_files = user_config_parser.get_user_info_by_yaml_from_directory(
            Path.cwd() / "config" / "users"
        )
        logger.info(f"User count from file: {len(user_list_from_files)}")
        users_obj_dict.update(user_list_from_files)
    if user_from_group_center:
        user_list_from_group_center = (
            user_config_parser.get_json_user_config_from_group_center()
        )
        logger.info(f"User count from Group Center: {len(user_list_from_group_center)}")
        users_obj_dict.update(user_list_from_group_center)

    logger.info(f"Final user count: {len(users_obj_dict)}")

    return users_obj_dict


def set_iptables(port: int) -> None:
    cmd_list = [
        f"sudo iptables -I INPUT -p tcp --dport {port} -j ACCEPT",
        f"sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port {port}",
        f"sudo ip6tables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port {port}",
    ]
    for cmd in cmd_list:
        try:
            common_utils.do_command(cmd)
        except Exception as e:
            logger.warning(f"Set iptables error: {e} when executing {cmd}")

    logger.info("Set iptables success!")
