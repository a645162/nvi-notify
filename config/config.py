from utils import env

import json
import os

gpu_monitor_usage_threshold = env.get_env_int("GPU_MONITOR_USAGE_THRESHOLD", 20)

gpu_monitor_sleep_time = env.get_env_int("GPU_MONITOR_SLEEP_TIME", 5)

web_server_host = '0.0.0.0'
web_server_port = 1234


# https://developer.work.weixin.qq.com/document/path/91770
def parse_user_list(file_path: str):
    if not file_path:
        return []

    if not file_path.endswith('.json'):
        return []

    if not os.path.exists(file_path):
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        return_list = list(json.load(f))

    for user in return_list:
        if not user.get('user_id'):
            user['user_id'] = "Unknown"

        if not user.get('keywords'):
            user['keywords'] = []

        if not user.get('mention_id'):
            user['mention_id'] = ""

        if not user.get('mention_phone_number'):
            user['mention_phone_number'] = ""

    return return_list


user_list = parse_user_list('config/user_list.json')
print()

if __name__ == '__main__':
    print()

    print(f"gpu_monitor_usage_threshold: {gpu_monitor_usage_threshold}")
    print(f"gpu_monitor_sleep_time: {gpu_monitor_sleep_time}")
    print(f"web_server: {web_server_host}:{web_server_port}")
    print()
