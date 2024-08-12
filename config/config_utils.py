import datetime
import os

from config.user_info import UserConfigParser, UserInfo
from feature.utils.logs import get_logger
from feature.utils.common_utils import do_command

logger = get_logger()


def is_webhook_sleep_time(
    start_time: datetime.time = None, end_time: datetime.time = None
) -> bool:
    if start_time is None or end_time is None:
        from config.settings import (WEBHOOK_SLEEP_TIME_END,
                                     WEBHOOK_SLEEP_TIME_START)

        start_time = WEBHOOK_SLEEP_TIME_START
        end_time = WEBHOOK_SLEEP_TIME_END

    if is_within_time_range(start_time, end_time):
        return True
    else:
        return False


def is_within_time_range(
    start_time=datetime.time(11, 0), end_time=datetime.time(7, 30)
) -> bool:
    current_time = datetime.datetime.now().time()

    if start_time <= end_time:
        return start_time <= current_time <= end_time
    else:
        return start_time <= current_time or current_time <= end_time


def get_seconds_to_sleep_until_end(end_time=None) -> float:
    if end_time is None:
        from config.settings import WEBHOOK_SLEEP_TIME_END

        end_time = WEBHOOK_SLEEP_TIME_END

    current_datetime = datetime.datetime.now()
    current_time = current_datetime.time()
    end_datetime = datetime.datetime.combine(current_datetime.date(), end_time)

    if end_time <= current_time:
        end_datetime += datetime.timedelta(days=1)

    time_to_sleep = (end_datetime - current_datetime).total_seconds()

    return time_to_sleep  # 返回整数秒数


def get_users():
    users_obj_dict: dict[str, UserInfo] = {}
    user_config_parser = UserConfigParser()
    from config.settings import USE_GROUP_CENTER, EnvironmentManager

    user_from_group_center = USE_GROUP_CENTER and EnvironmentManager.get_bool(
        "USER_FROM_GROUP_CENTER", False
    )
    user_from_local_files = EnvironmentManager.get_bool("USER_FROM_LOCAL_FILES", True)

    if user_from_local_files:
        user_list_from_files = user_config_parser.get_user_info_by_yaml_from_directory(
            os.path.join(os.getcwd(), "config/users")
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


def set_iptables(port: str) -> None:
    cmd_list = [
        f"sudo iptables -I INPUT -p tcp --dport {port} -j ACCEPT",
        f"sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port {port}",
        f"sudo ip6tables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port {port}",
    ]
    for cmd in cmd_list:
        try:
            do_command(cmd)
        except Exception as e:
            logger.warning(f"Set iptables error: {e} when executing {cmd}")

    logger.info("Set iptables success!")
