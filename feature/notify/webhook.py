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

from config.settings import WEBHOOK_NAME
from config.user_info import UserInfo
from config.utils import get_seconds_to_sleep_until_end, is_webhook_sleep_time
from feature.monitor.monitor_enum import AllWebhookName, MsgType, WebhookState
from feature.utils.logs import get_logger

logger = get_logger()


class Webhook:
    def __init__(self, webhook_name: str, webhook_url_header: str) -> None:
        self.webhook_name = webhook_name.lower()
        if not AllWebhookName.check_value_valid(self.webhook_name):
            logger.error(f"{webhook_name}'s webhook is not supported!")
            raise ValueError(f"{webhook_name}'s webhook is not supported!")
        self.webhook_url_header = webhook_url_header.lower().strip()

        self._webhook_url_main = self.get_webhook_url(
            os.getenv(f"WEBHOOK_{webhook_name.upper()}_DEPLOY")
        )
        self._webhook_url_warning = self.get_webhook_url(
            os.getenv(f"WEBHOOK_{webhook_name.upper()}_DEV")
        )

        self._webhook_secret_main = os.getenv(
            f"WEBHOOK_{webhook_name.upper()}_DEPLOY_SECRET", ""
        )
        self._webhook_secret_warning = os.getenv(
            f"WEBHOOK_{webhook_name.upper()}_DEV_SECRET", ""
        )

        self._webhook_state = WebhookState.WORKING

        self.msg_queue = Queue()
        self.retry_msg_queue = Queue(maxsize=3)

    @property
    def webhook_url_main(self) -> str:
        return self._webhook_url_main

    @webhook_url_main.setter
    def webhook_url_main(self, value: str) -> None:
        if value:
            self._webhook_url_main = value.strip()

    @property
    def webhook_url_warning(self) -> str:
        return self._webhook_url_warning

    @webhook_url_warning.setter
    def webhook_url_warning(self, value: str) -> None:
        if value:
            self._webhook_url_warning = value.strip()

    @property
    def webhook_secret_main(self) -> str:
        return self._webhook_secret_main

    @webhook_secret_main.setter
    def webhook_secret_main(self, value: str) -> None:
        if value:
            self._webhook_secret_main = value.strip()

    @property
    def webhook_secret_warning(self) -> str:
        return self._webhook_secret_warning

    @webhook_secret_warning.setter
    def webhook_secret_warning(self, value: str) -> None:
        if value:
            self._webhook_secret_warning = value.strip()

    def get_webhook_url(self, webhook_api: str):
        webhook_api = webhook_api.strip()
        if len(webhook_api) == 0:
            logger.error(f"Illegal {self.webhook_name} Webhook!")
            return ""

        return (
            webhook_api
            if webhook_api.startswith(self.webhook_url_header)
            else self.webhook_url_header + webhook_api
        )

    def get_message(self) -> str:
        if self.retry_msg_queue.empty():
            msg = self.msg_queue.get()  # blocking
        else:  # msg, msg_type, user
            msg = self.retry_msg_queue.get()
        return msg

    def send_message(
        self,
        msg: str,
        msg_type: str = MsgType.NORMAL,
        user: UserInfo = None,
        mention_everyone: bool = False,
    ):
        raise NotImplementedError(f"{self.webhook_name} should implement this method.")

    def check_webhook_state(self) -> None:
        while is_webhook_sleep_time():
            sleep_seconds = get_seconds_to_sleep_until_end()
            logger.info(f"[{self.webhook_name}] Sleep seconds: {sleep_seconds}")
            if self._webhook_state != WebhookState.SLEEPING:
                self.webhook_state = WebhookState.SLEEPING
            time.sleep(sleep_seconds)
        if self._webhook_state != WebhookState.WORKING:
            self.webhook_state = WebhookState.WORKING

    def webhook_send_thread(self) -> None:
        while True:
            self.check_webhook_state()
            current_msg = self.get_message()
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
        mention_everyone: bool = False,
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
        if user is not None:  # when mention everyone, user is None
            mention_everyone = False

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
            webhook_thread[webhook_name].msg_queue.put(
                (msg, msg_type, user, mention_everyone)
            )
            logger.info(f"{webhook_name}消息队列添加一条消息。")

    @staticmethod
    def enqueue_warning_msg_for_user_to_webhook(
        msg: str, user: UserInfo, mention_everyone: bool = False
    ):
        msg = msg.strip()
        if len(msg) == 0:
            logger.warning("Message is empty!")
            return

        webhook_thread["lark"].msg_queue.put(
            (msg, MsgType.DISK_WARNING_TO_USER, user, mention_everyone)
        )
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
    MentionAll = '<at user_id="all">所有人</at>'

    def __init__(self, webhook_name: str) -> None:
        webhook_url_header = "https://open.feishu.cn/open-apis/bot/v2/hook/"
        super().__init__(webhook_name, webhook_url_header)
        self.lark_app_url = (
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=user_id"
        )
        self._lark_app_id = os.getenv("LARK_APP_ID", "")
        self._lark_app_secret = os.getenv("LARK_APP_SECRET", "")

    @property
    def lark_app_id(self):
        return self._lark_app_id

    @lark_app_id.setter
    def lark_app_id(self, value):
        if value:
            self._lark_app_id = value.strip()

    @property
    def lark_app_secret(self):
        return self._lark_app_secret

    @lark_app_secret.setter
    def lark_app_secret(self, value):
        if value:
            self._lark_app_secret = value.strip()

    def send_message(
        self,
        msg: str,
        msg_type: MsgType = MsgType.NORMAL,
        user: UserInfo = None,
        mention_everyone: bool = False,
    ):
        # send msg to user by lark app
        self.send_lark_message_by_app(msg, msg_type, user)
        if msg_type == MsgType.DISK_WARNING_TO_USER:
            # only send dir size warning msg to user
            return

        keyword = "main" if msg_type == MsgType.NORMAL else "warning"
        webhook_url = getattr(self, f"webhook_url_{keyword}")
        if len(webhook_url) == 0:
            return
        webhook_secret = getattr(self, f"webhook_secret_{keyword}")

        # send msg to lark group
        self.send_lark_message(msg, webhook_url, webhook_secret, user, mention_everyone)

    def send_lark_message(
        self,
        msg: str,
        webhook_url: str,
        webhook_secret: str,
        user: UserInfo = None,
        mention_everyone: bool = False,
    ):
        headers = {"Content-Type": "application/json"}
        msg = msg.replace("/::D", "[呲牙]")

        if not mention_everyone:
            mention_header = self.get_group_msg_mention_header(user)
            if len(mention_header) > 0:
                mention_header += " "
                msg = msg.replace(user.name_cn, mention_header, 1)
        else:
            msg += self.MentionAll

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

    def get_group_msg_mention_header(self, user: UserInfo = None) -> str:
        if user is None:
            return ""

        lark_mention_ids = user.lark_info.get("mention_id", [""])
        if lark_mention_ids == [""]:
            return ""

        mention_header = " ".join(
            f'<at user_id="ou_{mention_id}">{user.name_cn}</at>'
            for mention_id in lark_mention_ids
        )
        return mention_header

    def send_lark_message_by_app(
        self, msg: str, msg_type: MsgType, user: UserInfo = None
    ):
        tenant_access_token = self.get_lark_app_tenant_access_token()
        if (
            len(self.lark_app_id) == 0
            or len(self.lark_app_secret) == 0
            or len(tenant_access_token) == 0
            or user is None
            or msg_type == MsgType.WARNING
        ):
            return

        headers = {
            "Authorization": f"Bearer {tenant_access_token}",
            "Content-Type": "application/json",
        }

        lark_mention_ids = user.lark_info.get("mention_id", [""])
        if len(lark_mention_ids) > 1 and len(lark_mention_ids[0]) == 0:
            return

        msg = msg.replace("/::D", "[呲牙]")
        if msg.find("完成") != -1:
            msg = msg.replace(f"{user.name_cn}的", "任务", 1)

        data = {
            "content": json.dumps({"text": msg}),
            "msg_type": "text",
            "receive_id": lark_mention_ids[0],
        }
        _ = requests.post(self.lark_app_url, headers=headers, data=json.dumps(data))
        logger.info(f"LarkApp[To{user.name_cn}]消息发送成功")

    def get_lark_app_tenant_access_token(self) -> str:
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
        webhook_url_header = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key="
        super().__init__(webhook_name, webhook_url_header)

    def send_message(
        self,
        msg: str,
        msg_type: str = MsgType.NORMAL,
        user: UserInfo = None,
        mention_everyone: bool = False,
    ):
        keyword = "main" if msg_type == MsgType.NORMAL else "warning"
        webhook_url = getattr(self, f"webhook_url_{keyword}")
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
