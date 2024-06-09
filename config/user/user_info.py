# -*- coding: utf-8 -*-


class UserInfo:
    def __init__(self, user_dict: dict) -> None:
        self.name_cn: str = user_dict.get("name", "")
        self.name_eng: str = user_dict.get("nameEng", "")
        self.keywords: list[str] = user_dict.get("keywords", [])
        self.year: int = user_dict.get("year", 2021)

        webhook_dict: dict = user_dict.get("webhook", {})
        self.wecom_info: dict[str, list[str]] = self.get_webhook_info(
            webhook_dict, webhook_type="weCom"
        )
        self.lark_info: dict[str, list[str]] = self.get_webhook_info(
            webhook_dict, webhook_type="lark"
        )

    @staticmethod
    def get_webhook_info(
        webhook_dict: dict, webhook_type: str = "weCom"
    ) -> dict[str, list]:
        if webhook_type in webhook_dict.keys():
            mention_id = webhook_dict[webhook_type].get("userId", [""])
            mention_mobile = webhook_dict[webhook_type].get("userMobilePhone", [""])
            if not isinstance(mention_id, list):
                mention_id = [mention_id]
            if not isinstance(mention_mobile, list):
                mention_mobile = [mention_mobile]
            return {
                "mention_id": mention_id,
                "mention_mobile": mention_mobile,
            }
        else:
            return {
                "mention_id": [""],
                "mention_mobile": [""],
            }
