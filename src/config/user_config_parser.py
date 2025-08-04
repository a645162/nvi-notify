import json
from pathlib import Path

import chardet
import yaml

from src.config.user_info import UserInfo


class UserConfigParser:
    def get_user_info_by_json(self, directory: Path = Path()) -> dict[str, UserInfo]:
        json_files = self.get_user_config_files(directory, "json")
        dict_list = []

        for file in json_files:
            with Path.open(file) as f:
                content: dict = json.load(f)

            if "version" not in content or "enable" not in content:
                continue

            if str(content["enable"]).lower() != "true":
                continue

            dict_list.extend(content["userList"])

        return self.get_user_info_obj_dict(dict_list)

    def get_user_info_by_yaml(self, directory: Path = Path()) -> dict[str, UserInfo]:
        yaml_files = self.get_user_config_files(directory, "yaml")
        dict_list = []

        for file in yaml_files:
            content: dict = self.parse_yaml(file)
            if "version" not in content or "enable" not in content:
                continue

            if str(content["enable"]).lower() != "true":
                continue

            dict_list.extend(content["userList"])

        return self.get_user_info_obj_dict(dict_list)

    def get_user_config_from_remote(self) -> dict[str, UserInfo]:
        from group_center.core.feature import remote_config  # noqa: PLC0415

        json_str = remote_config.get_user_config_json_str()

        if len(json_str) == 0:
            return {}

        dict_list = json.loads(json_str)

        if not isinstance(dict_list, list):
            return {}

        return self.get_user_info_obj_dict(dict_list)

    @staticmethod
    def get_user_info_obj_dict(dict_list: list[dict]) -> dict[str, UserInfo]:
        user_info_obj_dict: dict[str, UserInfo] = {}

        for user_dict in dict_list:
            if not isinstance(user_dict, dict):
                continue

            current_user_info = UserInfo(user_dict)
            user_info_obj_dict[current_user_info.name_eng] = current_user_info

        return user_info_obj_dict

    @staticmethod
    def get_user_config_files(
        directory: Path = Path(), extension: str = "yaml"
    ) -> list[Path]:
        if not directory.exists():
            directory = Path(__file__).resolve().parent
            print("Default User Dir:", directory)

        recursive = True
        glob_func = directory.rglob if recursive else directory.glob
        files_list = [p for p in glob_func(f"*.{extension}")]

        return files_list

    @staticmethod
    def parse_yaml(yaml_file: Path) -> dict:
        # Check Encoding
        with Path.open(yaml_file, "rb") as f:
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
