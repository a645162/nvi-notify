import json
import threading
import time
from typing import List

import requests

from config.settings import (
    WEBHOOK_SLEEP_TIME_END,
    WEBHOOK_SLEEP_TIME_START,
    WEBHOOK_WEWORK_DEPLOY,
    WEBHOOK_WEWORK_DEV,
    get_now_time,
    is_within_time_range,
)


def get_wework_url(wework_webhook: str) -> str:
    wework_webhook = wework_webhook.strip()

    if len(wework_webhook) == 0:
        print("Illegal WeWork Webhook!")
        return ""

    webhook_header = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key="

    if wework_webhook.startswith(webhook_header):
        return wework_webhook
    else:
        return webhook_header + wework_webhook


webhook_url_main = get_wework_url(WEBHOOK_WEWORK_DEPLOY)
webhook_url_warning = get_wework_url(WEBHOOK_WEWORK_DEV)


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
        except Exception:
            mentioned_id = []

    if not isinstance(mentioned_mobile, List):
        try:
            mentioned_mobile = [str(mentioned_mobile)]
        except Exception:
            mentioned_mobile = []

    if len(webhook_url) == 0:
        print("Illegal WeWork Webhook!")
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
        msg: str,
        mentioned_id: List[str] = None,
        mentioned_mobile: List[str] = None,
        msg_type: str = "normal",
) -> None:
    """Send text message in any time.

    Args:
        msg_type (str): choice=['normal', 'warning']. Defaults to "normal".

    Raises:
        ValueError: "msg_type must be 'normal' or 'warning'"
    """
    assert msg_type in ["normal", "warning"]

    if msg_type == "normal":
        webhook_url = webhook_url_main
    elif msg_type == "warning":
        webhook_url = webhook_url_warning
    else:
        print("msg_type must be 'normal' or 'warning'")
        return

    direct_send_text_with_url(
        webhook_url=webhook_url,
        msg=msg,
        mentioned_id=mentioned_id,
        mentioned_mobile=mentioned_mobile,
    )


msg_queue = []
thread_is_start = False


def send_text_thread() -> None:
    while True:
        if len(msg_queue) == 0:
            time.sleep(5)
            continue
        try:
            if is_within_time_range(WEBHOOK_SLEEP_TIME_START, WEBHOOK_SLEEP_TIME_END):
                time.sleep(60)
                continue

            current_msg = msg_queue[0]
            direct_send_text_with_url(*current_msg)
            msg_queue.pop(0)
            print(f"[{get_now_time()}]消息队列发送一条消息。")

        except Exception:
            time.sleep(60)


def send_text(
        msg: str,
        mentioned_id=None,
        mentioned_mobile=None,
        msg_type: str = "normal",
) -> None:
    """Send text message in non-sleep time.

    Args:
        msg_type (str): choice=['normal', 'warning']. Defaults to "normal".

    Raises:
        ValueError: "msg_type must be 'normal' or 'warning'"
    """
    assert msg_type in ["normal", "warning"]

    if msg_type == "normal":
        webhook_url = webhook_url_main
    elif msg_type == "warning":
        webhook_url = webhook_url_warning
    else:
        print("msg_type must be 'normal' or 'warning'")
        return

    webhook_url = webhook_url.strip()
    if len(webhook_url) == 0:
        return

    msg_queue.append((webhook_url, msg, mentioned_id, mentioned_mobile))
    print(f"[{get_now_time()}]消息队列添加一条消息。")
    global thread_is_start
    if not thread_is_start:
        thread_is_start = True
        threading.Thread(target=send_text_thread).start()


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
    send_text(
        f"GPU Monitor\n"
        f"\tMachine Name: {machine_name}\n"
        f"\tTime: {formatted_time}\n"
        f"Test Pass!\n",
        mentioned_id=["khm"],
        mentioned_mobile=None,
        msg_type="warning",
    )
