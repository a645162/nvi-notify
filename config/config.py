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

    # parse json array to list
    with open(file_path, 'r', encoding='utf-8') as f:
        return list(json.load(f))


user_list = parse_user_list('user_list_exp.json')
print()

if __name__ == '__main__':
    print()

    print(f"gpu_monitor_usage_threshold: {gpu_monitor_usage_threshold}")
    print(f"gpu_monitor_sleep_time: {gpu_monitor_sleep_time}")
    print(f"web_server: {web_server_host}:{web_server_port}")
    print()
