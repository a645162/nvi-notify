import json

from config.user.user_info import UserInfo


def parse_json_user_config(json_str: str) -> dict[str, UserInfo]:
    dict_list = json.loads(json_str)

    if not isinstance(dict_list, list):
        return {}

    user_list_dict: dict[str, UserInfo] = {}

    for user_dict in dict_list:
        if not isinstance(user_dict, dict):
            continue

        current_user_info = UserInfo(user_dict)
        user_list_dict[current_user_info.name_eng] = current_user_info

    return user_list_dict


def parse_json_user_config_directory():
    pass


def get_json_user_config_from_group_center() -> dict[str, UserInfo]:
    from feature.group_center. \
        group_center_remote_config import get_user_config_json_str

    json_str = get_user_config_json_str()

    return parse_json_user_config(json_str)


if __name__ == "__main__":
    with open("test.json", "r") as f:
        text = f.read()

    user_list_dict = parse_json_user_config(text)

    print()
