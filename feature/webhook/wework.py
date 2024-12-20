import json

import requests

from config.user_info import UserInfo
from feature.monitor.monitor_enum import MsgType
from feature.webhook.webhook import Webhook
from feature.utils.logs import get_logger

logger = get_logger()


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
        mentioned_list = [""]
        mentioned_mobile_list = [""]

        if user is not None:
            mentioned_list = user.wecom_info.get("mention_id", [""])
            mentioned_mobile_list = user.wecom_info.get("mention_mobile", [""])

        if mention_everyone:
            mentioned_list = ["@all"]
            # mentioned_mobile_list = ["@all"]
            mentioned_mobile_list = [""]

        data = {
            "msgtype": "text",
            "text": {
                "content": msg,
                "mentioned_list": list(set(mentioned_list)),
                "mentioned_mobile_list": list(set(mentioned_mobile_list)),
            },
        }

        r = requests.post(webhook_url, headers=headers, data=json.dumps(data))
        logger.info(f"WeCom[text]{r.text}")
