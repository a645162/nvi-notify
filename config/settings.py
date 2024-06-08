# -*- coding: utf-8 -*-

import datetime
import os
import subprocess
import sys
from typing import Union

from dotenv import dotenv_values, load_dotenv
from nvitop import Device

from config.user import get_all_user_info
from config.utils import get_interface_ip_dict
from monitor.info.enum import AllWebhookName
from utils.logs import get_logger

logger = get_logger()

path_base = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def get_ip(ip_type: str = "v4"):
    assert ip_type in ["v4", "v6"]
    ip_dict = get_interface_ip_dict(ip_type)
    for interface_name, ip in ip_dict.items():
        return ip


def get_env_time(time_str: str, default: datetime.time = None) -> datetime.time:
    index = time_str.find(":")
    if index == -1:
        return default

    time_str_1 = time_str[:index].strip()
    time_str_2 = time_str[index + 1 :].strip()

    try:
        int_1 = int(time_str_1)
        int_2 = int(time_str_2)

        return datetime.time(int_1, int_2)
    except Exception as e:
        logger.error(f"{time_str}=>\n\t{time_str_1}|{time_str_2}\n\t=>{e}")
        return default


def get_now_time():
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    return formatted_time


def is_within_time_range(
    start_time=datetime.time(11, 0), end_time=datetime.time(7, 30)
):
    current_time = datetime.datetime.now().time()

    if start_time <= end_time:
        return start_time <= current_time <= end_time
    else:
        return start_time <= current_time or current_time <= end_time


def get_cpu_physics_num() -> int:
    command = "cat /proc/cpuinfo | grep 'physical id' | sort -u | wc -l"
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, text=True)

    if result.returncode == 0:
        return int(result.stdout.strip())


def get_emoji(key: Union[int, str]) -> str:
    EMOJI_DICT = {
        0: "0️⃣",
        1: "1️⃣",
        2: "2️⃣",
        3: "3️⃣",
        4: "4️⃣",
        5: "5️⃣",
        6: "6️⃣",
        7: "7️⃣",
        8: "8️⃣",
        9: "9️⃣",
        10: "🔟",
        "呲牙": "/::D",
    }
    if key not in EMOJI_DICT.keys():
        return "Unknown Emoji"
    return EMOJI_DICT[key]


def get_bool_from_string(string: str) -> bool:
    string = string.strip().lower()
    return string == "true"


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

    logger.info("=" * 40)
    for env_name, env in env_vars.items():
        logger.info(f"{env_name}: {env}")
    logger.info("=" * 40)


load_env()

IPv4 = get_ip("v4")
IPv6 = get_ip("v6")

USERS = get_all_user_info(os.path.join(os.getcwd(), "config/users"))
NUM_CPU = get_cpu_physics_num()
NUM_GPU = Device.count()

# Server Info
SERVER_NAME = os.getenv("SERVER_NAME", None)
SERVER_NAME_SHORT = os.getenv("SERVER_NAME_SHORT", "")
SERVER_DOMAIN = os.getenv("SERVER_DOMAIN", None)

# CPU Monitor
CPU_HIGH_TEMPERATURE_THRESHOLD = int(os.getenv("HIGH_TEMPERATURE_THRESHOLD", 85))
TEMPERATURE_MONITOR_SAMPLING_INTERVAL = int(
    os.getenv("TEMPERATURE_MONITOR_SAMPLING_INTERVAL", 300)
)

# GPU Monitor
GPU_MONITOR_SAMPLING_INTERVAL = int(os.getenv("GPU_MONITOR_SAMPLING_INTERVAL", 5))

# Hard Disk Monitor
HARD_DISK_MOUNT_POINT = [
    m.strip() for m in os.getenv("HARD_DISK_MOUNT_POINT", "/").split(",")
]
HARD_DISK_HIGH_PERCENTAGE_THRESHOLD = int(
    os.getenv("HARD_DISK_HIGH_PERCENTAGE_THRESHOLD", 95)
)
HARD_DISK_LOW_FREE_GB_THRESHOLD = int(os.getenv("HARD_DISK_LOW_FREE_GB_THRESHOLD", 100))
HARD_DISK_MONITOR_SAMPLING_INTERVAL = int(
    os.getenv("HARD_DISK_MONITOR_SAMPLING_INTERVAL", 3600)
)

# Flask
FLASK_SERVER_HOST = os.getenv("FLASK_SERVER_HOST", "0,0,0,0")
FLASK_SERVER_PORT = os.getenv("FLASK_SERVER_PORT", "3000")
GPU_BOARD_WEB_URL = os.getenv("GPU_BOARD_WEB_URL", "")

# Group Center
USE_GROUP_CENTER: bool = get_bool_from_string(os.getenv("USE_GROUP_CENTER", "FALSE"))
GROUP_CENTER_URL = os.getenv("GROUP_CENTER_URL", "http://127.0.0.1:8088")
GROUP_CENTER_PASSWORD = os.getenv("GROUP_CENTER_PASSWORD", "password")

# WebHook
WEBHOOK_DELAY_SEND_SECONDS = int(os.getenv("WEBHOOK_DELAY_SEND_SECONDS", 60))
WEBHOOK_SLEEP_TIME_START = get_env_time(
    os.getenv("WEBHOOK_SLEEP_TIME_START", "23:00"), datetime.time(23, 0)
)
WEBHOOK_SLEEP_TIME_END = get_env_time(
    os.getenv("WEBHOOK_SLEEP_TIME_END", "8:00"), datetime.time(8, 0)
)

WEBHOOK_NAME = [
    m.strip().upper()
    for m in os.getenv("WEBHOOK_NAME", AllWebhookName.WEWORK).split(",")
]
WEBHOOK_WEWORK_DEPLOY = os.getenv("WEBHOOK_WEWORK_DEPLOY", "").strip()
WEBHOOK_WEWORK_DEV = os.getenv("WEBHOOK_WEWORK_DEV", "").strip()
WEBHOOK_LARK_DEPLOY = os.getenv("WEBHOOK_LARK_DEPLOY", "").strip()
WEBHOOK_LARK_DEV = os.getenv("WEBHOOK_LARK_DEV", "").strip()

GPU_MONITOR_AUTO_RESTART = get_bool_from_string(
    os.getenv("GPU_MONITOR_AUTO_RESTART", "True").strip()
)


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
    # env_path = Path(".") / ".env"
    # load_dotenv(dotenv_path=env_path, verbose=True)

    print(is_within_time_range(datetime.time(23, 00), datetime.time(7, 30)))
