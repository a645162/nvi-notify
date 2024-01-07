import os
import time
import threading
import requests
import json

from utils import my_time
from utils import env

import datetime

ENV_VAR_NAME = "GPU_MONITOR_WEBHOOK_WEWORK"


def get_wework_url():
    wework_env = env.get_env(ENV_VAR_NAME)
    if not wework_env:
        print(f"{ENV_VAR_NAME} Not Set!")
        return None

    # Judge is URL
    if wework_env.startswith('http'):
        return wework_env

    webhook_url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=' + wework_env
    return webhook_url


def direct_send_text(msg: str, mentioned_id=None, mentioned_mobile=None):
    if mentioned_mobile is None:
        mentioned_mobile = []
    if mentioned_id is None:
        mentioned_id = []

    webhook_url = get_wework_url()

    if not webhook_url:
        print(f"{ENV_VAR_NAME} Not Set!")
        return

    headers = {'Content-Type': 'application/json'}
    data = {
        "msgtype": "text",
        "text": {
            "content": msg
        }
    }

    if mentioned_id:
        data["text"]["mentioned_list"] = mentioned_id
    if mentioned_mobile:
        data["text"]["mentioned_mobile_list"] = mentioned_mobile

    r = requests.post(webhook_url, headers=headers, data=json.dumps(data))
    print("WeWork", "text", r.text)


def direct_send_markdown(content: str):
    webhook_url = get_wework_url()

    if not webhook_url:
        print("GPU_MONITOR_WEWORK 环境变量未设置")
        return

    headers = {'Content-Type': 'application/json'}
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "GPU Monitor",
            "content": content
        }
    }
    r = requests.post(webhook_url, headers=headers, data=json.dumps(data))
    print("WeWork", "MarkDown", r.text)


msg_queue = []
thread_is_start = False

sleep_time_start = (
    env.get_env_time(
        "GPU_MONITOR_SLEEP_TIME_START",
        datetime.time(23, 0))
)
sleep_time_end = (
    env.get_env_time(
        "GPU_MONITOR_SLEEP_TIME_END",
        datetime.time(7, 30))
)

is_in_sleep_time = False


def send_text_thread():
    global is_in_sleep_time

    while True:
        if len(msg_queue) == 0:
            time.sleep(5)
            continue
        if is_in_sleep_time:
            if my_time.is_within_time_range(sleep_time_start, sleep_time_end):
                time.sleep(60)
                continue
            else:
                is_in_sleep_time = False

        try:
            current_msg = msg_queue[0]
            direct_send_text(current_msg[0], current_msg[1], current_msg[2])
            msg_queue.pop(0)
        except:
            time.sleep(60)


def send_text(msg: str, mentioned_id=None, mentioned_mobile=None):
    msg_queue.append((msg, mentioned_id, mentioned_mobile))
    global thread_is_start
    if not thread_is_start:
        thread_is_start = True
        threading.Thread(target=send_text_thread).start()


if __name__ == '__main__':
    import socket

    # 获取当前机器的名称
    machine_name = socket.gethostname()
    print("当前机器名称:", machine_name)

    formatted_time = my_time.get_now_time()
    print("当前时间:", formatted_time)

    # 发送测试数据
    send_text(
        f"GPU Monitor\n"
        f"\tMachine Name: {machine_name}\n"
        f"\tTime: {formatted_time}\n"
        f"Test Pass!\n",
        mentioned_id=["khm"]
    )

    # direct_send_markdown(
    #     f"# GPU Monitor\n"
    #     f"## Machine Name\n{machine_name}\n"
    #     f"## Time\n{formatted_time}\n"
    #     f"# Test Pass!\n"
    # )
