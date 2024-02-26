import datetime
import json
import threading
import time
from typing import List

import requests

from utils.env import get_env_str, get_env_time
from utils.time_utils import get_now_time, is_within_time_range

ENV_VAR_NAME = "GPU_MONITOR_WEBHOOK_WEWORK"
WARNING_ENV_NAME = "GPU_MONITOR_WEBHOOK_WEWORK_WARNING"

machine_name = get_env_str("SERVER_NAME", "")


def get_wework_url(webhook_env: str = "") -> str:
    if len(webhook_env.strip()) == 0:
        wework_env = get_env_str(ENV_VAR_NAME, "")
    else:
        wework_env = webhook_env.strip()

    if not wework_env:
        print(f"{ENV_VAR_NAME} Not Set!")
        return ""

    if len(wework_env) == 0:
        print(f"WeWork Key Env!")
        return ""

    # Judge is URL
    if wework_env.startswith("http"):
        return wework_env

    webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=" + wework_env
    return webhook_url


webhook_url_main = get_wework_url(get_env_str(ENV_VAR_NAME, ""))
webhook_url_warning = get_wework_url(get_env_str(WARNING_ENV_NAME, ""))


def direct_send_text_with_url(
    webhook_url: str,
    msg: str,
    mentioned_id: List[str] = None,
    mentioned_mobile: List[str] = None,
) -> None:
    if mentioned_mobile is None:
        mentioned_mobile = []
    if mentioned_id is None:
        mentioned_id = []

    if not isinstance(mentioned_id, List):
        try:
            mentioned_id = [str(mentioned_id)]
        except:
            mentioned_id = []

    if not isinstance(mentioned_mobile, List):
        try:
            mentioned_mobile = [str(mentioned_mobile)]
        except:
            mentioned_mobile = []

    if len(webhook_url) == 0:
        print(f"URL Not Set!")
        return

    headers = {"Content-Type": "application/json"}
    data = {"msgtype": "text", "text": {"content": msg}}

    if mentioned_id:
        data["text"]["mentioned_list"] = mentioned_id
    if mentioned_mobile:
        data["text"]["mentioned_mobile_list"] = mentioned_mobile

    r = requests.post(webhook_url, headers=headers, data=json.dumps(data))
    print("WeWork", "text", r.text)


def direct_send_text(
    msg: str, mentioned_id: List[str] = None, mentioned_mobile: List[str] = None
) -> None:
    direct_send_text_with_url(
        webhook_url=webhook_url_main,
        msg=msg,
        mentioned_id=mentioned_id,
        mentioned_mobile=mentioned_mobile,
    )


def direct_send_text_warning(
    msg: str, mentioned_id: List[str] = None, mentioned_mobile: List[str] = None
) -> None:
    direct_send_text_with_url(
        webhook_url=webhook_url_warning,
        msg=msg,
        mentioned_id=mentioned_id,
        mentioned_mobile=mentioned_mobile,
    )


msg_queue = []
thread_is_start = False

sleep_time_start = get_env_time("GPU_MONITOR_SLEEP_TIME_START", datetime.time(23, 0))
sleep_time_end = get_env_time("GPU_MONITOR_SLEEP_TIME_END", datetime.time(7, 30))


def send_text_thread() -> None:
    while True:
        if len(msg_queue) == 0:
            time.sleep(5)
            continue
        try:
            if is_within_time_range(sleep_time_start, sleep_time_end):
                time.sleep(60)
                continue

            current_msg = msg_queue[0]
            direct_send_text_with_url(
                current_msg[0], current_msg[1], current_msg[2], current_msg[3]
            )
            msg_queue.pop(0)
            print(f"[{get_now_time()}]消息队列发送一条消息。")

        except:
            time.sleep(60)


def send_text(
    webhook_url: str, msg: str, mentioned_id=None, mentioned_mobile=None
) -> None:
    webhook_url = webhook_url.strip()
    if len(webhook_url) == 0:
        return
    msg_queue.append((webhook_url, msg, mentioned_id, mentioned_mobile))
    print(f"[{get_now_time()}]消息队列添加一条消息。")
    global thread_is_start
    if not thread_is_start:
        thread_is_start = True
        threading.Thread(target=send_text_thread).start()


def send_text_normal(
    msg: str, mentioned_id: List[str] = None, mentioned_mobile: List[str] = None
) -> None:
    send_text(
        webhook_url=webhook_url_main,
        msg=msg,
        mentioned_id=mentioned_id,
        mentioned_mobile=mentioned_mobile,
    )


def send_text_warning(
    msg: str, mentioned_id: List[str] = None, mentioned_mobile: List[str] = None
) -> None:
    send_text(
        webhook_url=webhook_url_warning,
        msg=msg,
        mentioned_id=mentioned_id,
        mentioned_mobile=mentioned_mobile,
    )


if __name__ == "__main__":
    import socket

    # 获取当前机器的名称
    machine_name = socket.gethostname()
    print("当前机器名称:", machine_name)

    formatted_time = get_now_time()
    print("当前时间:", formatted_time)

    print(webhook_url_main)
    print(webhook_url_warning)

    # 发送测试数据
    send_text_warning(
        f"GPU Monitor\n"
        f"\tMachine Name: {machine_name}\n"
        f"\tTime: {formatted_time}\n"
        f"Test Pass!\n",
        mentioned_id=["khm"],
        mentioned_mobile=None,
    )
