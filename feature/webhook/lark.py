import datetime
import json
import os

import requests

from feature.config import user_info
from feature.monitor import enum
from feature.utils import logs
from feature.webhook import webhook

logger = logs.get_logger()


class LarkWebhook(webhook.Webhook):
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
    def lark_app_id(self) -> str:
        return self._lark_app_id

    @lark_app_id.setter
    def lark_app_id(self, value: str) -> None:
        if value:
            self._lark_app_id = value.strip()

    @property
    def lark_app_secret(self) -> str:
        return self._lark_app_secret

    @lark_app_secret.setter
    def lark_app_secret(self, value: str) -> None:
        if value:
            self._lark_app_secret = value.strip()

    def send_message(
        self,
        msg: str,
        msg_type: enum.MsgType = enum.MsgType.NORMAL,
        user: user_info.UserInfo | None = None,
        mention_everyone: bool = False,
    ) -> None:
        if msg_type != enum.MsgType.WARNING:
            # send msg to user by lark app
            self.send_lark_message_by_app(msg, msg_type, user)
            if msg_type == enum.MsgType.DISK_WARNING_TO_USER:
                # only send dir size warning msg to user
                return

        keyword = "main" if msg_type == enum.MsgType.NORMAL else "warning"
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
        user: user_info.UserInfo | None = None,
        mention_everyone: bool = False,
    ) -> None:
        headers = {"Content-Type": "application/json"}
        msg = msg.replace("/::D", "[呲牙]")

        if not mention_everyone:
            mention_header = self.get_group_msg_mention_header(user)
            if len(mention_header) > 0:
                mention_header += " "
                msg = msg.replace(user.name_cn, mention_header, 1) # type: ignore
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

    def get_group_msg_mention_header(self, user: user_info.UserInfo | None = None) -> str:
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
        self, msg: str, msg_type: enum.MsgType, user: user_info.UserInfo | None = None
    ) -> None:
        tenant_access_token = self.get_lark_app_tenant_access_token()
        if (
            len(self.lark_app_id) == 0
            or len(self.lark_app_secret) == 0
            or len(tenant_access_token) == 0
            or user is None
            or msg_type == enum.MsgType.WARNING
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
