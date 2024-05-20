# -*- coding: utf-8 -*-

import os
from typing import List

from config.utils import get_files_with_extension, parse_yaml


def get_user(yaml_content: dict) -> List[dict]:
    return_list = []

    for user_dict in yaml_content.values():
        user_dict["keywords"] = user_dict.get("keywords", [])
        user_dict["wework"] = user_dict.get("wework", {})
        user_dict["wework"]["mention_id"] = user_dict["wework"].get("mention_id", "")
        user_dict["wework"]["mention_mobile"] = user_dict["wework"].get("mention_mobile", "")

        return_list.append(user_dict)

    return return_list


def get_all_user_list(directory_path: str = "") -> List[dict]:
    all_user = []

    if len(directory_path) == 0:
        directory_path = os.path.dirname(os.path.abspath(__file__))
        print("Default User Dir:", directory_path)

    yaml_list = get_files_with_extension(directory_path, "yaml", True)
    for yaml_file_path in yaml_list:
        yaml_content: dict = parse_yaml(yaml_file_path)
        user_list = get_user(yaml_content)
        for user in user_list:
            all_user.append(user)

    return all_user


if __name__ == "__main__":
    # yaml_file_path = os.path.join(os.getcwd(), "config/users/master/2023.yaml")
    # yaml_content: dict = parse_yaml(yaml_file_path)
    yaml_file_path = os.path.join(os.getcwd(), "config/users")
    users_list: List[dict] = get_all_user_list(yaml_file_path)

    for user in users_list:
        print(user['name'])
        print(user['keywords'])
        print(user)
    # user_list: List[dict] = get_user(yaml_content)

    # for user in user_list:
    #     print(user)
