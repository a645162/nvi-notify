
import datetime
import hashlib
import base64
import hmac
import json
import threading
import time
from queue import Queue

import requests

from config.settings import (
    WEBHOOK_NAME,
    WEBHOOK_SLEEP_TIME_END,
    WEBHOOK_SLEEP_TIME_START,
    get_now_time,
    is_within_time_range,
)
from config.user import UserInfo
from utils.logs import get_logger

logger = get_logger()


class WEBHOOK:
    def __init__(self, webhook_type: str) -> None:
        valid_webhook_type = ["wework", "lark"]
        assert (
            webhook_type.lower() in valid_webhook_type
        ), f"{webhook_type}'s webhook is not supported!"

        self.webhook_type = webhook_type
        self.webhook_url_main_varname = f"WEBHOOK_{webhook_type.upper()}_DEPLOY"
        self.webhook_url_warning_varname = f"WEBHOOK_{webhook_type.upper()}_DEV"
        self.webhook_secret_varname = f"WEBHOOK_{webhook_type.upper()}_SECRET"
        self.webhook_url_main = self.get_webhook_url(
            locals()[self.webhook_url_main_varname.strip()]
        )
        self.webhook_url_warning = self.get_webhook_url(
            locals()[self.webhook_url_warning_varname.strip()]
        )
        self.webhook_secret = locals()[self.webhook_secret_varname.strip()]

        self.msg_queue = Queue()
        self.thread_is_start = False
        self._webhook_state = "working"

    def get_webhook_url(self, webhook_api):
        webhook_api = webhook_api.strip()

        if len(webhook_api) == 0:
            logger.error(f"Illegal {self.webhook_type} Webhook!")
            return ""
        if self.webhook_type.lower() == "wework":
            webhook_header = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key="
        elif self.webhook_type.lower() == "lark":
            webhook_header = "https://open.feishu.cn/open-apis/bot/v2/hook/"

        if webhook_api.startswith(webhook_header):
            return webhook_api
        else:
            return webhook_header + webhook_api

    def send_message(self, msg: str, msg_type: str = "normal", user: UserInfo = None):
        if msg_type == "normal":
            webhook_url = self.get_webhook_url(self.webhook_url_main)
        elif msg_type == "warning":
            webhook_url = self.get_webhook_url(self.webhook_url_warning)

        if self.webhook_type == "wework":
            self.send_weCom_message(user, msg, webhook_url)
        elif self.webhook_type == "lark":
            self.send_lark_message(user, msg, webhook_url)

    def send_weCom_message(self, msg: str, webhook_url: str, user: UserInfo = None):
        headers = {"Content-Type": "application/json"}
        data = {
            "msgtype": "text",
            "text": {
                "content": msg,
            },
        }
        if user is not None:
            data["text"].update(
                {
                    "mentioned_list": user.wecom_info.get("mention_id", [""]),
                    "mentioned_mobile_list": user.wecom_info.get(
                        "mention_mobile", [""]
                    ),
                }
            )
        r = requests.post(webhook_url, headers=headers, data=json.dumps(data))
        logger.info(f"WeCom[text]{r.text}")

    def send_lark_message(self, msg: str, webhook_url: str, user: UserInfo = None):
        headers = {"Content-Type": "application/json"}
        if user is None:
            lark_menion_ids = [""]
        else:
            lark_menion_ids = user.lark_info.get("mention_id", [""])

        if len(lark_menion_ids) == 0:
            mention_header = ""
        elif len(lark_menion_ids) == 1:
            if lark_menion_ids[0] == "":
                mention_header = ""
            else:
                mention_header = (
                    f'<at user_id = "ou_{lark_menion_ids[0]}">{user.name_cn}</at>'
                )
        else:
            mention_header = [
                f'<at user_id = "ou_{lark_menion_id}">{user.name_cn}</at>'
                for lark_menion_id in lark_menion_ids
            ]

        if len(mention_header) >= 0:
            mention_header += " "
        now_timestamp = datetime.datetime.now().timestamp()
        data = {
            "timestamp": now_timestamp,
            "sign": self.gen_sign(now_timestamp, self.webhook_secret),
            "msg_type": "text",
            "content": {
                "text": mention_header + msg,
            },
        }

        r = requests.post(webhook_url, headers=headers, data=json.dumps(data))
        logger.info(f"Lark[text]{r.text}")

    def webhook_send_thread(self) -> None:
        while True:
            self.check_webhook_state()
            if self.msg_queue.empty():
                time.sleep(5)
                continue
            try:
                current_msg = self.msg_queue.get_nowait()  # msg, msg_type, user
                self.send_message(*current_msg)
                if self.msg_queue.task_done():
                    logger.info(f"[{get_now_time()}]消息队列发送一条消息。")

                # 每分钟最多20条消息
                time.sleep(3.1)

            except Exception:
                logger.warning(f"[{get_now_time()}]消息队列发送异常。")
                time.sleep(60)

    def check_webhook_state(self):
        if is_within_time_range(WEBHOOK_SLEEP_TIME_START, WEBHOOK_SLEEP_TIME_END):
            self._work_state = "sleeping"
            time.sleep(60)
        else:
            self._work_state = "working"

    @property
    def webhook_state(self):
        return self._work_state

    @webhook_state.setter
    def webhook_state(self, cur_webhook_state):
        if self._work_state == cur_webhook_state:
            return
        else:
            logger.info(
                f"[{get_now_time()}][{self.webhook_type}]webhook状态切换为{cur_webhook_state}。"
            )

        self._work_state = cur_webhook_state

    @staticmethod
    def gen_sign(timestamp, secret):
        # 拼接timestamp和secret
        string_to_sign = "{}\n{}".format(timestamp, secret)
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        # 对结果进行base64处理
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return sign

thread_start_flags = {}

def send_text(
    msg: str, msg_type: str = "normal", user: UserInfo = None, webhook_type: str = "wework"
):
    """Send text message in non-sleep time.

    Args:
        msg_type (str): choice=['normal', 'warning']. Defaults to "normal".

    Raises:
        ValueError: "msg_type must be 'normal' or 'warning'"
    """
    assert msg_type in ["normal", "warning"], logger.error(
        "msg_type must be 'normal' or 'warning'"
    )

    msg = msg.strip()
    if len(msg) == 0:
        logger.warning("Message is empty!")
        return

    global thread_start_flags
    webhook_list = []

    for idx, webhook_type in enumerate(WEBHOOK_NAME):
        if webhook_type not in thread_start_flags:
            thread_start_flags[webhook_type] = True
            webhook_obj = WEBHOOK(webhook_type.lower())
            webhook_list.append(webhook_obj)
            threading.Thread(target=webhook_obj.send_text_thread).start()
            time.sleep(0.5)  # waiting

        webhook_list[idx].msg_queue.put((msg, msg_type, user))

    logger.info(f"[{get_now_time()}]消息队列添加一条消息。")
