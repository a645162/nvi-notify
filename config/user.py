# -*- coding: utf-8 -*-

import os
from typing import Dict

from utils.utils import get_files_with_extension, parse_yaml


class UserInfo:
    def __init__(self, user_dict: dict) -> None:
        self.name_cn: str = user_dict.get("name", "")
        self.name_eng: str = user_dict.get("nameEng", "")
        self.keywords: list[str] = user_dict.get("keywords", [])
        self.year: int = user_dict.get("year", 2021)

        webhook_dict: dict = user_dict.get("webhook", {})
        self.wecom_info: dict[str, dict[str, list[str]]] = self.get_webhook_info(
            webhook_dict, webhook_type="weCom"
        )
        self.lark_info: dict[str, dict[str, list[str]]] = self.get_webhook_info(
            webhook_dict, webhook_type="lark"
        )

    @staticmethod
    def get_webhook_info(
            webhook_dict: dict, webhook_type: str = "weCom"
    ) -> Dict[str, list]:
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


def get_all_user_info(directory_path: str = ""):
    all_user = {}

    if len(directory_path) == 0:
        directory_path = os.path.dirname(os.path.abspath(__file__))
        print("Default User Dir:", directory_path)

    yaml_list = get_files_with_extension(directory_path, "yaml", True)
    for yaml_file_path in yaml_list:
        yaml_content: dict = parse_yaml(yaml_file_path)
        if "version" not in yaml_content.keys():
            continue
        if "enable" not in yaml_content.keys():
            continue

        if str(yaml_content["enable"]).lower() != "true":
            continue

        users = {
            UserInfo(user).name_eng: UserInfo(user) for user in yaml_content["userList"]
        }
        all_user.update(users)

    return all_user


if __name__ == "__main__":
    # yaml_file_path = os.path.join(os.getcwd(), "config/users/master/2023.yaml")
    # yaml_content: dict = parse_yaml(yaml_file_path)
    yaml_file_path = os.path.join(os.getcwd(), "config/users_new")
    users = get_all_user_info(yaml_file_path)

    for user in users:
        print(user['name_cn'])
        print(user['keywords'])
        print(user)
