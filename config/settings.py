# -*- coding: utf-8 -*-

import datetime
import os
import platform
import socket
import sys

import psutil
from dotenv import dotenv_values, load_dotenv
from nvitop import Device
from packaging import version

from config.user.user_info import UserInfo
from config.user.user_parser import UserConfigParser
from feature.monitor.monitor_enum import AllWebhookName
from utils.logs import get_logger
from utils.utils import do_command

logger = get_logger()

path_base = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

all_env_dict: dict[str, str] = {}


def get_env_str(var: str, default: str) -> str:
    if var in all_env_dict:
        return all_env_dict[var].strip()

    return os.getenv(var, default).strip()


def get_env_bool(var: str, default: bool) -> bool:
    assert isinstance(default, bool), logger.error(
        f'Env "{var}" default must be bool, but get {type(default)}'
    )

    value = get_env_str(var, str(default))
    return value.strip().lower() == "true"


def get_env_int(var: str, default: int) -> int:
    try:
        return int(os.getenv(var))
    except Exception as e:
        logger.error(f"[var]{e}")
        return default


def get_env_time(var: str, default: datetime.time) -> datetime.time:
    value = get_env_str(var, "")
    try:
        return datetime.datetime.strptime(value, "%H:%M").time()
    except ValueError as e:
        logger.error(f"{e}")
        return default


def is_webhook_sleep_time() -> bool:
    if is_within_time_range(WEBHOOK_SLEEP_TIME_START, WEBHOOK_SLEEP_TIME_END):
        return True
    else:
        return False


def get_users():
    users_obj_dict: dict[str, UserInfo] = {}
    user_config_parser = UserConfigParser()

    user_from_group_center = USE_GROUP_CENTER and get_env_bool(
        "USER_FROM_GROUP_CENTER", False
    )
    user_from_local_files = get_env_bool("USER_FROM_LOCAL_FILES", True)

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


def get_ip(ip_type: str = "v4") -> str:
    assert ip_type in ["v4", "v6"]
    ip_dict = get_interface_ip_dict(ip_type)
    for ip in ip_dict.values():
        return ip


def load_env():
    default_env_file = os.path.join(path_base, ".env")

    if os.path.exists(default_env_file):
        load_dotenv(default_env_file, verbose=True)
        env_vars = dotenv_values(default_env_file)
    else:
        logger.error("default env file not found")
        return

    if sys.gettrace():
        extend_env_file = os.path.join(os.getcwd(), ".env.dev")
    else:
        extend_env_file = os.path.join(os.getcwd(), ".env.secure")

    if os.path.exists(extend_env_file):
        new_env_vars = dotenv_values(extend_env_file)
        load_dotenv(extend_env_file, verbose=True, override=True)
        env_vars.update(new_env_vars)

    global all_env_dict
    all_env_dict = env_vars

    logger.info("=" * 40)
    for env_name, env in env_vars.items():
        logger.info(f"{env_name}: {env}")
    logger.info("=" * 40)


def check_sudo_permission() -> bool:
    return os.geteuid() == 0


def check_python_version(min_required_version: str) -> str:
    """
    Check if the current Python version is greater than or equal to the minimum required version.

    :param min_required_version: The minimum required Python version as a string.
    :return: True if the current Python version is greater than or equal to the minimum required version, False otherwise.
    """
    current_version = platform.python_version()

    assert version.parse(current_version) >= version.parse(
        min_required_version
    ), logger.error(
        "Python version must be greater than or equal to {}".format(
            min_required_version
        )
    )

    return current_version


def get_interface_ip_dict(ip_type: str = "v4") -> dict:
    interface_ip_dict = {}
    family = socket.AF_INET if ip_type == "v4" else socket.AF_INET6

    # get local ip from dns
    try:
        if ip_type == "v4":
            s = socket.socket(family, socket.SOCK_DGRAM)
            s.connect(("114.114.114.114", 80))
        elif ip_type == "v6":
            s = socket.socket(family, socket.SOCK_DGRAM)
            s.connect(("6.ipw.cn", 80))
        local_ip = s.getsockname()[0]
    except Exception as e:
        logger.error(f"Error getting local IP: {e}")
        local_ip = None
    finally:
        s.close()

    interface_name_list = [
        interface_name.strip()
        for interface_name in psutil.net_if_addrs().keys()
        if interface_name.strip()
    ]

    # get local ip by psutil
    for interface_name in interface_name_list:
        for addr in psutil.net_if_addrs().get(interface_name, []):
            try:
                if addr.family == family:
                    if ip_type == "v4":
                        socket.inet_aton(addr.address)
                    elif ip_type == "v6":
                        socket.inet_pton(family, addr.address)
                    if addr.address == local_ip:
                        interface_ip_dict[interface_name] = addr.address
                    break
            except socket.error:
                pass
    return interface_ip_dict


def now_time_str() -> str:
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    return formatted_time


def is_within_time_range(
    start_time=datetime.time(11, 0), end_time=datetime.time(7, 30)
) -> bool:
    current_time = datetime.datetime.now().time()

    if start_time <= end_time:
        return start_time <= current_time <= end_time
    else:
        return start_time <= current_time or current_time <= end_time


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


load_env()

# Init
WAIT_TIME_BEFORE_START = int(get_env_int("WAIT_TIME_BEFORE_START", 10))
SUDO_PERMISSION = check_sudo_permission()
PYTHON_VERSION = check_python_version("3.10")

# Network
IPv4 = get_ip("v4")
IPv6 = get_ip("v6")

# GPU
NUM_GPU = Device.count()

# Server Info
SERVER_NAME = get_env_str("SERVER_NAME", "None")
SERVER_NAME_SHORT = get_env_str("SERVER_NAME_SHORT", "")
SERVER_DOMAIN = get_env_str("SERVER_DOMAIN", "None")

# Group Center
USE_GROUP_CENTER = get_env_bool("USE_GROUP_CENTER", False)
GROUP_CENTER_URL = get_env_str("GROUP_CENTER_URL", "http://localhost:8088")
GROUP_CENTER_PASSWORD = get_env_str("GROUP_CENTER_PASSWORD", "password")
ENV_FROM_GROUP_CENTER = USE_GROUP_CENTER and get_env_bool(
    "ENV_FROM_GROUP_CENTER", False
)
if ENV_FROM_GROUP_CENTER:
    from feature.group_center.group_center_remote_config import init_remote_env_list

    init_remote_env_list()

# CPU Monitor
CPU_HIGH_TEMPERATURE_THRESHOLD = int(get_env_int("CPU_HIGH_TEMPERATURE_THRESHOLD", 85))
TEMPERATURE_MONITOR_SAMPLING_INTERVAL = int(
    get_env_int("TEMPERATURE_MONITOR_SAMPLING_INTERVAL", 300)
)

# GPU Monitor
GPU_MONITOR_SAMPLING_INTERVAL = int(get_env_int("GPU_MONITOR_SAMPLING_INTERVAL", 5))
GPU_MONITOR_AUTO_RESTART = get_env_bool("GPU_MONITOR_AUTO_RESTART", True)

# Hard Disk Monitor
HARD_DISK_MOUNT_POINT = set(
    m.strip() for m in get_env_str("HARD_DISK_MOUNT_POINT", "/").split(",")
)
HARD_DISK_MONITOR_SAMPLING_INTERVAL = int(
    get_env_int("HARD_DISK_MONITOR_SAMPLING_INTERVAL", 3600)
)
HARD_DISK_HIGH_PERCENTAGE_THRESHOLD = int(
    get_env_int("HARD_DISK_HIGH_PERCENTAGE_THRESHOLD", 95)
)
HARD_DISK_LOW_FREE_GB_THRESHOLD = int(
    get_env_int("HARD_DISK_LOW_FREE_GB_THRESHOLD", 100)
)

# Flask
FLASK_SERVER_HOST = get_env_str("FLASK_SERVER_HOST", "0.0.0.0")
FLASK_SERVER_PORT = get_env_str("FLASK_SERVER_PORT", "3000")
GPU_BOARD_WEB_URL = get_env_str("GPU_BOARD_WEB_URL", "")

# WebHook
WEBHOOK_DELAY_SEND_SECONDS = int(get_env_int("WEBHOOK_DELAY_SEND_SECONDS", 60))
WEBHOOK_SEND_LAUNCH_MESSAGE = get_env_bool("WEBHOOK_SEND_LAUNCH_MESSAGE", True)
WEBHOOK_SLEEP_TIME_START = get_env_time(
    "WEBHOOK_SLEEP_TIME_START", datetime.time(23, 0)
)
WEBHOOK_SLEEP_TIME_END = get_env_time("WEBHOOK_SLEEP_TIME_END", datetime.time(8, 0))

WEBHOOK_NAME = set(
    m.strip().upper()
    for m in get_env_str("WEBHOOK_NAME", AllWebhookName.WEWORK.value).split(",")
)
WEBHOOK_WEWORK_DEPLOY = get_env_str("WEBHOOK_WEWORK_DEPLOY", "")
WEBHOOK_WEWORK_DEV = get_env_str("WEBHOOK_WEWORK_DEV", "")

WEBHOOK_LARK_DEPLOY = get_env_str("WEBHOOK_LARK_DEPLOY", "")
WEBHOOK_LARK_DEV = get_env_str("WEBHOOK_LARK_DEV", "")

# User
USERS: dict[str, UserInfo] = get_users()
if SUDO_PERMISSION:
    set_iptables(FLASK_SERVER_PORT)


def fix_env():
    def fix_url():
        global GROUP_CENTER_URL

        if not GROUP_CENTER_URL.startswith("http"):
            GROUP_CENTER_URL = f"http://{GROUP_CENTER_URL}"

        if not GROUP_CENTER_URL.endswith("/"):
            GROUP_CENTER_URL += "/"

    fix_url()


fix_env()

if __name__ == "__main__":
    load_dotenv(dotenv_path="", verbose=True)
