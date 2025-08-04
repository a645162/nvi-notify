import base64
import hashlib
import hmac
import os
import threading
import time
from queue import Queue

from nvi_notify.config import settings, user_info
from nvi_notify.monitor import enums as monitor_enums
from nvi_notify.utils import config_utils, logs
from nvi_notify.webhook import enums as webhook_enums

logger = logs.get_logger()


class Webhook:
    def __init__(self, name: str, webhook_url_header: str) -> None:
        self.name = name.lower()
        if not webhook_enums.AllWebhookName.check_value_valid(self.name):
            logger.error(f"{name}'s webhook is not supported!")
            raise ValueError(f"{name}'s webhook is not supported!")

        self.webhook_url_header = webhook_url_header.lower().strip()

        self._webhook_url_main = self.get_webhook_url(
            os.getenv(f"WEBHOOK_{name.upper()}_DEPLOY")  # type: ignore
        )
        self._webhook_url_warning = self.get_webhook_url(
            os.getenv(f"WEBHOOK_{name.upper()}_DEV")  # type: ignore
        )

        self._webhook_secret_main = os.getenv(
            f"WEBHOOK_{name.upper()}_DEPLOY_SECRET", ""
        )
        self._webhook_secret_warning = os.getenv(
            f"WEBHOOK_{name.upper()}_DEV_SECRET", ""
        )

        self._webhook_state = webhook_enums.WebhookState.WORKING

        self.msg_queue = Queue()
        self.warning_msg_queue = Queue()
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

    def get_webhook_url(self, webhook_api: str) -> str:
        webhook_api = webhook_api.strip()
        if len(webhook_api) == 0:
            logger.warning(f"Illegal {self.name} Webhook!")
            return ""

        return (
            webhook_api
            if webhook_api.startswith(self.webhook_url_header)
            else self.webhook_url_header + webhook_api
        )

    def get_message(self) -> tuple:
        if self.retry_msg_queue.empty():
            msg = self.msg_queue.get()  # 阻塞获取消息
        else:
            msg = self.retry_msg_queue.get()
        return msg

    def get_warning_message(self) -> tuple:
        msg = self.warning_msg_queue.get()
        return msg

    def send_message(  # noqa: ANN201
        self,
        msg: str,
        msg_type: monitor_enums.MsgType = monitor_enums.MsgType.NORMAL,
        user: user_info.UserInfo | None = None,
        mention_everyone: bool = False,
    ):
        raise NotImplementedError(f"{self.name} should implement this method.")

    def check_webhook_state(self) -> None:
        while config_utils.is_webhook_quiet_period():
            sleep_seconds = config_utils.get_seconds_until_webhook_wake_up()
            logger.info(f"[{self.name}] Sleep seconds: {sleep_seconds}")
            if self._webhook_state != webhook_enums.WebhookState.SLEEPING:
                self.webhook_state = webhook_enums.WebhookState.SLEEPING
            time.sleep(sleep_seconds)
        if self._webhook_state != webhook_enums.WebhookState.WORKING:
            self.webhook_state = webhook_enums.WebhookState.WORKING

    def webhook_main_thread(self) -> None:
        logger.info(f"{self.name}消息线程启动。")
        while True:
            current_msg = self.get_message()
            self.check_webhook_state()
            try:
                self.send_message(*current_msg)
                logger.info(f"{self.name}消息队列发送一条消息。")
                time.sleep(3.1)  # 每分钟最多20条消息
            except Exception as e:
                logger.warning(
                    f"{self.name}消息队列发送异常，进行重试。exception:{e}",
                )
                self.retry_msg_queue.put(current_msg)
                time.sleep(5)

    def webhook_warning_thread(self) -> None:
        logger.info(f"{self.name}报警消息线程启动。")
        while True:
            current_msg = self.get_warning_message()
            try:
                self.send_message(*current_msg)
                logger.info(f"{self.name}报警消息队列发送一条消息。")
                time.sleep(3.1)  # 每分钟最多20条消息
            except Exception as e:
                logger.warning(
                    f"{self.name}报警消息队列发送异常。exception:{e}",
                )
                time.sleep(5)

    @property
    def webhook_state(self) -> webhook_enums.WebhookState:
        return self._webhook_state

    @webhook_state.setter
    def webhook_state(self, cur_webhook_state: webhook_enums.WebhookState) -> None:
        if self._webhook_state != cur_webhook_state:
            logger.debug(f"[{self.name}]webhook状态切换为{cur_webhook_state}。")
            self._webhook_state = cur_webhook_state

    @staticmethod
    def enqueue_msg_to_webhook(
        msg: str,
        msg_type: monitor_enums.MsgType = monitor_enums.MsgType.NORMAL,
        user: user_info.UserInfo | None = None,
        mention_everyone: bool = False,
        enable_name: list[webhook_enums.AllWebhookName]
        | webhook_enums.AllWebhookName = webhook_enums.AllWebhookName.ALL,
    ) -> None:
        assert msg_type == monitor_enums.MsgType.NORMAL, logger.error(
            "msg_type must be in enum.MsgType.NORMAL"
        )
        assert isinstance(enable_name, webhook_enums.AllWebhookName), logger.error(
            "enable_name must be in settings.WEBHOOK_NAME env, or 'enum.AllWebhookName.ALL'"
        )
        if user is not None:  # when mention everyone, user is None
            mention_everyone = False

        enable_name_list: list[str] = (
            enable_name.value
            if isinstance(enable_name.value, list)
            else [enable_name.value]
        )

        msg = msg.strip()
        if len(msg) == 0:
            logger.warning("Message is empty!")
            return

        for name in enable_name_list:
            if name.upper() not in settings.WEBHOOK_NAME:
                continue
            webhook_thread[name].msg_queue.put_nowait(
                (msg, msg_type, user, mention_everyone)
            )
            logger.info(f"{name}消息队列添加一条消息。")

    @staticmethod
    def send_warning_msg_to_webhook_all_time(
        msg: str,
        msg_type: monitor_enums.MsgType,
        user: user_info.UserInfo | None = None,
        mention_everyone: bool = False,
    ) -> None:
        if msg_type != monitor_enums.MsgType.WARNING:
            raise ValueError("msg_type must be 'enum.MsgType.WARNING'")

        if user is not None and mention_everyone:
            raise ValueError("when mention everyone, user is None")

        msg = msg.strip()
        if len(msg) == 0:
            logger.warning("Message is empty!")
            return

        for name in settings.WEBHOOK_NAME:
            _name = name.lower()
            if _name not in webhook_thread.keys():
                continue
            webhook_thread[_name].warning_msg_queue.put(
                (msg, msg_type, user, mention_everyone)
            )
            logger.info(f"[{_name}]警告消息队列添加一条消息。")

    @staticmethod
    def enqueue_warning_msg_for_user_to_webhook(
        msg: str, user: user_info.UserInfo, mention_everyone: bool = False
    ) -> None:
        msg = msg.strip()
        if len(msg) == 0:
            logger.warning("Message is empty!")
            return

        webhook_thread["lark"].msg_queue.put(
            (msg, monitor_enums.MsgType.DISK_WARNING_TO_USER, user, mention_everyone)
        )
        logger.info(
            f"[LarkApp]消息队列添加一条发送至用户[{user.name_cn}]目录大小报警消息。"
        )

    @staticmethod
    def gen_sign(timestamp: int, secret: str) -> str:
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return sign


def init_webhook() -> None:
    from nvi_notify.webhook import lark, wework  # noqa: PLC0415

    webhook_classes = {
        webhook_enums.AllWebhookName.WEWORK.value: wework.WeworkWebhook,
        webhook_enums.AllWebhookName.LARK.value: lark.LarkWebhook,
    }

    global webhook_thread  # noqa: PLW0603
    webhook_thread = {}

    for _name in webhook_enums.AllWebhookName.ALL.value:  # 实例化所有webhook
        name = _name.lower()
        webhook_thread[name] = webhook_classes[name](name)
        threading.Thread(target=webhook_thread[name].webhook_main_thread).start()
        threading.Thread(target=webhook_thread[name].webhook_warning_thread).start()
