# -*- coding: utf-8 -*-
import json
from pathlib import Path

import chardet
import yaml


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
    def find_user_by_path(users: dict, path: str, is_project_path: bool = False):
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


class UserConfigParser:
    def get_user_info_by_json_from_directory(self) -> None:
        pass

    def get_json_user_config_from_group_center(self) -> dict[str, UserInfo]:
        from group_center.core.feature.remote_config import (
            get_user_config_json_str,
        )

        from feature.utils.logs import get_logger

        logger = get_logger()

        try:
            json_str = get_user_config_json_str()

            if len(json_str) == 0:
                logger.warning("Remote user config returned empty string, using local user configuration")
                return {}

            return self.get_user_info_by_json(json_str)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse remote user config JSON: {e}. Using local user configuration.")
            return {}
        except Exception as e:
            logger.warning(f"Failed to get remote user configuration: {e}. Using local user configuration.")
            return {}

    def get_user_info_by_json(self, json_str: str) -> dict[str, UserInfo]:
        dict_list = json.loads(json_str)

        if not isinstance(dict_list, list):
            return {}

        user_info_obj_dict: dict[str, UserInfo] = self.get_user_info_obj_dict(dict_list)

        return user_info_obj_dict

    def get_user_info_by_yaml_from_directory(
        self, directory: Path = Path()
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
        directory: Path = Path(), extension: str = "yaml"
    ) -> list[Path]:
        if not directory.exists():
            directory = Path(__file__).resolve().parent
            print("Default User Dir:", directory)

        recursive = True
        if recursive:
            files_path_list = [p for p in directory.rglob(f"**/*.{extension}")]
        else:
            files_path_list = [p for p in directory.glob(f"*.{extension}")]

        return files_path_list

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
