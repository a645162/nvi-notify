import base64
import datetime
import hashlib
import hmac
import json
import os
import threading
import time
from queue import Queue
from typing import Union

import requests

from config.settings import WEBHOOK_NAME, is_webhook_sleep_time
from config.user.user_info import UserInfo
from feature.monitor.monitor_enum import AllWebhookName, MsgType, WebhookState
from utils.logs import get_logger

logger = get_logger()


class Webhook:
    def __init__(self, webhook_name: str, webhook_header: str) -> None:
        self.webhook_name = webhook_name.lower()
        assert AllWebhookName.check_value_valid(self.webhook_name), logger.error(
            f"{webhook_name}'s webhook is not supported!"
        )
        self.webhook_header = webhook_header.lower().strip()

        self._webhook_url_main = self.get_webhook_url(
            os.getenv(f"WEBHOOK_{webhook_name.upper()}_DEPLOY")
        )
        self._webhook_url_warning = self.get_webhook_url(
            os.getenv(f"WEBHOOK_{webhook_name.upper()}_DEV")
        )

        self._webhook_main_secret = os.getenv(
            f"WEBHOOK_{webhook_name.upper()}_DEPLOY_SECRET", ""
        )
        self._webhook_warning_secret = os.getenv(
            f"WEBHOOK_{webhook_name.upper()}_DEV_SECRET", ""
        )

        self._webhook_state = WebhookState.WORKING

        self.msg_queue = Queue()
        self.retry_msg_queue = Queue(maxsize=3)

    @property
    def webhook_url_main(self):
        return self._webhook_url_main

    @webhook_url_main.setter
    def webhook_url_main(self, value):
        if value is not None:
            self._webhook_url_main = value.strip()

    @property
    def webhook_url_warning(self):
        return self._webhook_url_warning

    @webhook_url_warning.setter
    def webhook_url_warning(self, value):
        if value is not None:
            self._webhook_url_warning = value.strip()

    @property
    def webhook_main_secret(self):
        return self._webhook_main_secret

    @webhook_main_secret.setter
    def webhook_main_secret(self, value):
        if value is not None:
            self._webhook_main_secret = value.strip()

    @property
    def webhook_warning_secret(self):
        return self._webhook_warning_secret

    @webhook_warning_secret.setter
    def webhook_warning_secret(self, value):
        if value is not None:
            self._webhook_warning_secret = value.strip()

    def get_webhook_url(self, webhook_api: str):
        webhook_api = webhook_api.strip()
        if len(webhook_api) == 0:
            logger.error(f"Illegal {self.webhook_name} Webhook!")
            return ""

        if webhook_api.startswith(self.webhook_header):
            return webhook_api
        else:
            return self.webhook_header + webhook_api

    def send_message(
        self, msg: str, msg_type: str = MsgType.NORMAL, user: UserInfo = None
    ):
        raise NotImplementedError("Subclasses should implement this method.")

    def check_webhook_state(self) -> None:
        while is_webhook_sleep_time():
            if self._webhook_state != WebhookState.SLEEPING:
                self.webhook_state = WebhookState.SLEEPING
            time.sleep(60)
        if self._webhook_state != WebhookState.WORKING:
            self.webhook_state = WebhookState.WORKING

    def webhook_send_thread(self) -> None:
        while True:
            self.check_webhook_state()
            if self.msg_queue.empty() and self.retry_msg_queue.empty():
                time.sleep(5)
                continue

            current_msg = (
                self.msg_queue.get()
                if self.retry_msg_queue.empty()
                else self.retry_msg_queue.get()
            )  # msg, msg_type, user

            try:
                self.send_message(*current_msg)
                logger.info(f"{self.webhook_name}消息队列发送一条消息。")
                time.sleep(3.1)  # 每分钟最多20条消息
            except Exception as e:
                logger.warning(
                    f"{self.webhook_name}消息队列发送异常，进行重试。exception:{e}",
                )
                self.retry_msg_queue.put(current_msg)
                time.sleep(5)

    @property
    def webhook_state(self) -> WebhookState:
        return self._webhook_state

    @webhook_state.setter
    def webhook_state(self, cur_webhook_state) -> None:
        if self._webhook_state != cur_webhook_state:
            logger.debug(f"[{self.webhook_name}]webhook状态切换为{cur_webhook_state}。")
            self._webhook_state = cur_webhook_state

    @staticmethod
    def enqueue_msg_to_webhook(
        msg: str,
        msg_type: MsgType = MsgType.NORMAL,
        user: UserInfo = None,
        enable_webhook_name: Union[
            list[AllWebhookName], AllWebhookName
        ] = AllWebhookName.ALL,
    ):
        assert isinstance(msg_type, MsgType), logger.error(
            "msg_type must be in MsgType"
        )
        assert isinstance(enable_webhook_name, AllWebhookName), logger.error(
            "enable_webhook_name must be in WEBHOOK_NAME env, or 'AllWebhookName.ALL'"
        )

        enable_webhook_name_list: list[str] = (
            enable_webhook_name.value
            if isinstance(enable_webhook_name.value, list)
            else [enable_webhook_name.value]
        )

        msg = msg.strip()
        if len(msg) == 0:
            logger.warning("Message is empty!")
            return

        for webhook_name in enable_webhook_name_list:
            if webhook_name.upper() not in WEBHOOK_NAME:
                continue
            webhook_thread[webhook_name].msg_queue.put((msg, msg_type, user))
            logger.info(f"{webhook_name}消息队列添加一条消息。")

    @staticmethod
    def enqueue_warning_msg_for_user_to_webhook(msg: str, user: UserInfo):
        msg = msg.strip()
        if len(msg) == 0:
            logger.warning("Message is empty!")
            return

        webhook_thread["lark"].msg_queue.put((msg, MsgType.DISK_WARNING_TO_USER, user))
        logger.info(
            f"[LarkApp]消息队列添加一条发送至用户[{user.name_cn}]目录大小报警消息。"
        )

    @staticmethod
    def gen_sign(timestamp: int, secret: str) -> str:
        string_to_sign = "{}\n{}".format(timestamp, secret)
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return sign


class LarkWebhook(Webhook):
    def __init__(self, webhook_name: str) -> None:
        webhook_header = "https://open.feishu.cn/open-apis/bot/v2/hook/"
        super().__init__(webhook_name, webhook_header)
        self._lark_app_id = os.getenv("LARK_APP_ID", "")
        self._lark_app_secret = os.getenv("LARK_APP_SECRET", "")

    @property
    def lark_app_id(self):
        return self._lark_app_id

    @lark_app_id.setter
    def lark_app_id(self, value):
        if value is not None:
            self._lark_app_id = value.strip()

    @property
    def lark_app_secret(self):
        return self._lark_app_secret

    @lark_app_secret.setter
    def lark_app_secret(self, value):
        if value is not None:
            self._lark_app_secret = value.strip()

    def send_message(
        self, msg: str, msg_type: str = MsgType.NORMAL, user: UserInfo = None
    ):
        # only send dir size warning msg to user
        if msg_type == MsgType.DISK_WARNING_TO_USER:
            self.send_lark_message_by_app(msg, user)
            return

        webhook_url = (
            self.webhook_url_main
            if msg_type == MsgType.NORMAL
            else self.webhook_url_warning
        )
        webhook_secret = (
            self.webhook_main_secret
            if msg_type == MsgType.NORMAL
            else self.webhook_warning_secret
        )

        if len(webhook_url) == 0:
            return

        self.send_lark_message(msg, webhook_url, webhook_secret, user)
        self.send_lark_message_by_app(msg, user)

    def send_lark_message(
        self, msg: str, webhook_url: str, webhook_secret: str, user: UserInfo = None
    ):
        headers = {"Content-Type": "application/json"}
        msg = msg.replace("/::D", "[呲牙]")
        if user is None:
            lark_mention_ids = [""]
        else:
            lark_mention_ids = user.lark_info.get("mention_id", [""])

        mention_header = ""
        if len(lark_mention_ids) > 0:
            if lark_mention_ids[0] != "":
                mention_header = " ".join(
                    f'<at user_id="ou_{mention_id}">{user.name_cn}</at>'
                    for mention_id in lark_mention_ids
                )

        if len(mention_header) > 0:
            mention_header += " "
            msg = msg.replace(user.name_cn, mention_header, 1)
        now_timestamp = int(datetime.datetime.now().timestamp())
        data = {
            "timestamp": now_timestamp,
            "sign": self.gen_sign(now_timestamp, webhook_secret),
            "msg_type": "text",
            "content": {
                "text": msg,
            },
        }

        r = requests.post(webhook_url, headers=headers, data=json.dumps(data))
        logger.info(f"Lark[text]{r.text}")

    def send_lark_message_by_app(self, msg: str, user: UserInfo = None):
        if len(self.lark_app_id) <= 0 or len(self.lark_app_secret) <= 0 or user is None:
            return

        webhook_url_header = (
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=user_id"
        )
        if self.get_lark_tenant_access_token() == "":
            return

        headers = {
            "Authorization": f"Bearer {self.get_lark_tenant_access_token()}",
            "Content-Type": "application/json",
        }

        lark_mention_ids = user.lark_info.get("mention_id", [""])

        if len(lark_mention_ids) == 1 and lark_mention_ids[0] != "":
            lark_mention_id = lark_mention_ids[0]
        else:
            return

        msg = msg.replace("/::D", "[呲牙]")
        msg = msg.replace(f"{user.name_cn}的", "任务", 1)

        data = {
            "content": json.dumps({"text": msg}),
            "msg_type": "text",
            "receive_id": lark_mention_id,
        }
        r = requests.post(webhook_url_header, headers=headers, data=json.dumps(data))
        logger.info(f"LarkApp[To{user.name_cn}]消息发送成功")

    def get_lark_tenant_access_token(self) -> str:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = json.dumps(
            {
                "app_id": self.lark_app_id,
                "app_secret": self.lark_app_secret,
            }
        )

        headers = {"Content-Type": "application/json"}

        try:
            r = requests.post(url, headers=headers, data=payload)
            if len(r.text) > 0:
                return r.text.split(":")[-1].split('"')[1]
            else:
                return ""
        except Exception:
            return ""


class WeworkWebhook(Webhook):
    def __init__(self, webhook_name: str) -> None:
        webhook_header = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key="
        super().__init__(webhook_name, webhook_header)

    def send_message(
        self, msg: str, msg_type: str = MsgType.NORMAL, user: UserInfo = None
    ):
        webhook_url = (
            self.webhook_url_main
            if msg_type == MsgType.NORMAL
            else self.webhook_url_warning
        )
        if len(webhook_url) == 0:
            return

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


def init_webhook():
    webhook_classes = {
        AllWebhookName.WEWORK.value: WeworkWebhook,
        AllWebhookName.LARK.value: LarkWebhook,
    }

    global webhook_thread
    webhook_thread = {}
    for webhook_name in AllWebhookName.ALL.value:  # 实例化所有webhook
        webhook_name = webhook_name.lower()
        webhook_thread[webhook_name] = webhook_classes[webhook_name](webhook_name)
        threading.Thread(
            target=webhook_thread[webhook_name].webhook_send_thread
        ).start()
