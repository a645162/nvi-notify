import json
import os
from glob import glob

import chardet
import yaml

from config.user.user_info import UserInfo


class UserConfigParser:
    def get_user_info_by_json_from_directory(self):
        pass

    def get_json_user_config_from_group_center(self) -> dict[str, UserInfo]:
        from feature.group_center.group_center_remote_config import (
            get_user_config_json_str,
        )

        json_str = get_user_config_json_str()

        if len(json_str) == 0:
            return {}

        return self.get_user_info_by_json(json_str)

    def get_user_info_by_json(self, json_str: str) -> dict[str, UserInfo]:
        dict_list = json.loads(json_str)

        if not isinstance(dict_list, list):
            return {}

        user_info_obj_dict: dict[str, UserInfo] = self.get_user_info_obj_dict(dict_list)

        return user_info_obj_dict

    def get_user_info_by_yaml_from_directory(
        self, directory: str = ""
    ) -> dict[str, UserInfo]:
        yaml_files_path_list = self.get_user_config_files_path(directory, "yaml")
        dict_list = []

        for yaml_file_path in yaml_files_path_list:
            yaml_content: dict = self.parse_yaml(yaml_file_path)
            if "version" not in yaml_content.keys():
                continue
            if "enable" not in yaml_content.keys():
                continue

            if str(yaml_content["enable"]).lower() != "true":
                continue

            dict_list.extend(yaml_content["userList"])

        user_info_obj_dict: dict[str, UserInfo] = self.get_user_info_obj_dict(dict_list)

        return user_info_obj_dict

    @staticmethod
    def get_user_info_obj_dict(dict_list) -> dict[str, UserInfo]:
        user_info_obj_dict: dict[str, UserInfo] = {}

        for user_dict in dict_list:
            if not isinstance(user_dict, dict):
                continue

            current_user_info = UserInfo(user_dict)
            user_info_obj_dict[current_user_info.name_eng] = current_user_info

        return user_info_obj_dict

    @staticmethod
    def get_user_config_files_path(
        directory: str = "", extension: str = "yaml"
    ) -> list:
        if len(directory) == 0:
            directory = os.path.dirname(os.path.abspath(__file__))
            print("Default User Dir:", directory)

        recursive = True
        if recursive:
            search_path = os.path.join(directory, f"**/*.{extension}")
        else:
            search_path = os.path.join(directory, f"*.{extension}")

        files_path_list = glob(search_path, recursive=recursive)

        return files_path_list

    @staticmethod
    def parse_yaml(yaml_file: str) -> dict:
        # Check Encoding
        with open(yaml_file, "rb") as f:
            raw_data = f.read()
            result_encoding = chardet.detect(raw_data)
            encoding = result_encoding["encoding"]

            if encoding is None:
                encoding = "utf-8"

        file_content = raw_data.decode(encoding).strip()

        if len(file_content) == 0:
            return {}

        yaml_data = yaml.safe_load(file_content)

        return yaml_data
