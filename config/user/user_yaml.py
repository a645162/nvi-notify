import os

from config.user.user_info import UserInfo
from config.utils import get_files_with_extension, parse_yaml


def parse_yaml_user_config_directory(directory_path: str = "") -> dict[str, UserInfo]:
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
    users = parse_yaml_user_config_directory(yaml_file_path)

    for user in users:
        print(user['name_cn'])
        print(user['keywords'])
        print(user)
