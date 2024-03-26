import os
from typing import Union

from config.env import get_env_int, get_env_str
from config.user import get_all_user_list

server_name = get_env_str("SERVER_NAME")
gpu_monitor_sleep_time = get_env_int("GPU_MONITOR_SLEEP_TIME", 5)
delay_send_seconds = get_env_int("DELAY_SEND_SECONDS", 60)
all_valid_user_list = get_all_user_list(os.path.join(os.getcwd(), "config/users"))

web_host = ""  # "your domin" or None
flask_server_host = "0.0.0.0"
flask_server_port = 8081


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

SERVER_DOMAIN_DICT = {
    "server_name": "server_web_host",
}


def get_emoji(key: Union[int, str]) -> str:
    if key not in EMOJI_DICT.keys():
        return "Unknown Emoji"
    return EMOJI_DICT[key]


if __name__ == "__main__":
    # print(f"gpu_monitor_usage_threshold: {gpu_monitor_usage_threshold}")
    # print(f"gpu_monitor_sleep_time: {gpu_monitor_sleep_time}")
    print(f"web_server: {flask_server_host}:{flask_server_port}")
