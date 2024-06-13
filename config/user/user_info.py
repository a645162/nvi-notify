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
    def find_user_by_path(users: dict, path: str, is_project_path:bool = False):
        if is_project_path:
            path = path.split("data")[1]
        for path_unit in reversed(path.split("/")):
            if path_unit == "":
                continue
            for user in users.values():
                if any(
                    path_unit.lower() == keyword.lower().strip()
                    for keyword in user.keywords
                ):
                    return user
        if is_project_path:
            raise RuntimeWarning("未获取到任务用户名")
        return None

    @staticmethod
    def get_webhook_info(
        webhook_dict: dict, webhook_type: str = "weCom"
    ) -> dict[str, list]:
        if webhook_type not in webhook_dict.keys():
            return {
                "mention_id": [""],
                "mention_mobile": [""],
            }

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
