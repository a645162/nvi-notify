import json
import os

from utils import env, ip

# local_ip = env.get_env("GPU_MONITOR_LOCAL_IP")
server_name = env.get_env_str("SERVER_NAME")
gpu_monitor_sleep_time = env.get_env_int("GPU_MONITOR_SLEEP_TIME", 5)
delay_send_seconds = env.get_env_int("DELAY_SEND_SECONDS", 60)

web_host = None
local_ip = ip.get_local_ip()
web_server_host = "0.0.0.0"
web_server_port = 8080

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


def get_emoji(key: (int, str)):
    if key not in EMOJI_DICT.keys():
        return "Unknown Emoji"
    return EMOJI_DICT[key]


# https://developer.work.weixin.qq.com/document/path/91770
def parse_user_list(file_path: str):
    if not file_path:
        return []

    if not file_path.endswith(".json"):
        return []

    if not os.path.exists(file_path):
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        return_list = list(json.load(f))

    for user in return_list:
        if not user.get("user_id"):
            user["user_id"] = "Unknown"

        if not user.get("keywords"):
            user["keywords"] = []

        if not user.get("mention_id"):
            user["mention_id"] = ""

        if not user.get("mention_phone_number"):
            user["mention_phone_number"] = ""

        for i in range(len(user["keywords"])):
            if len(user["keywords"][i].strip()) > 0:
                user["keywords"][i] = f"/{user['keywords'][i].lower()}/"

    return return_list


def parse_user_list_from_directory(directory_path: str) -> list:
    if not directory_path:
        return []

    if not os.path.exists(directory_path):
        return []

    return_list = []
    for file_name in os.listdir(directory_path):
        file_path = os.path.join(directory_path, file_name)

        if not file_path.endswith(".json"):
            continue

        return_list.extend(parse_user_list(file_path))

    return return_list


def read_user_list() -> list:
    current_user_list = []

    current_user_list.extend(parse_user_list("config/user_list.json"))

    return current_user_list


user_list = read_user_list()

if __name__ == "__main__":
    # print(f"gpu_monitor_usage_threshold: {gpu_monitor_usage_threshold}")
    print(f"gpu_monitor_sleep_time: {gpu_monitor_sleep_time}")
    print(f"web_server: {web_server_host}:{web_server_port}")
