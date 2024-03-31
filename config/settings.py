import datetime
import os
import subprocess
import sys
from typing import Union

from dotenv import dotenv_values, load_dotenv
from nvitop import Device

from config.users.utils import get_all_user_list
from config.utils import get_interface_ip_dict

path_base = os.path.dirname(
    os.path.dirname(
        os.path.realpath(__file__)
    )
)


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
    time_str_2 = time_str[index + 1:].strip()

    try:
        int_1 = int(time_str_1)
        int_2 = int(time_str_2)

        return datetime.time(int_1, int_2)
    except Exception as e:
        print(e)
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


def load_env():
    default_env_file = os.path.join(path_base, ".env")

    if os.path.exists(default_env_file):
        load_dotenv(default_env_file, verbose=True)
        env_vars = dotenv_values(default_env_file)
    else:
        raise FileNotFoundError("default env file not found")

    if sys.gettrace():
        extend_env_file = os.path.join(os.getcwd(), ".env.dev")
    else:
        extend_env_file = os.path.join(os.getcwd(), ".env.secure")

    if os.path.exists(extend_env_file):
        new_env_vars = dotenv_values(extend_env_file)
        load_dotenv(extend_env_file, verbose=True, override=True)
        env_vars.update(new_env_vars)

    print("=" * 40)
    for env_name, env in env_vars.items():
        print(f"{env_name}: {env}")
    print("=" * 40)


load_env()

IPv4 = get_ip("v4")
IPv6 = get_ip("v6")

USER_LIST = get_all_user_list(os.path.join(os.getcwd(), "config/users"))
NUM_CPU = get_cpu_physics_num()
NUM_GPU = Device.count()

# server info
SERVER_NAME = os.getenv("SERVER_NAME", None)
SERVER_DOMAIN = os.getenv("SERVER_DOMAIN", None)

# cpu monitor
CPU_HIGH_TEMPERATURE_THRESHOLD = int(os.getenv("HIGH_TEMPERATURE_THRESHOLD", 85))

# gpu monitor
GPU_MONITOR_SAMPLING_INTERVAL = int(os.getenv("GPU_MONITOR_SAMPLING_INTERVAL", 5))

# flask
FLASK_SERVER_HOST = os.getenv("FLASK_SERVER_HOST", "0,0,0,0")
FLASK_SERVER_PORT = os.getenv("FLASK_SERVER_PORT", "3000")
GPU_BOARD_WEB_URL = os.getenv("GPU_BOARD_WEB_URL", "")

# webhook
WEBHOOK_DELAY_SEND_SECONDS = int(os.getenv("WEBHOOK_DELAY_SEND_SECONDS", 60))
WEBHOOK_SLEEP_TIME_START = get_env_time(
    os.getenv("WEBHOOK_SLEEP_TIME_START", "23:00"), datetime.time(23, 0)
)
WEBHOOK_SLEEP_TIME_END = get_env_time(
    os.getenv("WEBHOOK_SLEEP_TIME_END", "8:00"), datetime.time(8, 0)
)

WEBHOOK_WEWORK_DEPLOY = os.getenv("WEBHOOK_WEWORK_DEPLOY", "")
WEBHOOK_WEWORK_DEV = os.getenv("WEBHOOK_WEWORK_DEV", "")

if __name__ == "__main__":
    # env_path = Path(".") / ".env"
    # load_dotenv(dotenv_path=env_path, verbose=True)

    print(is_within_time_range(datetime.time(23, 00), datetime.time(7, 30)))
