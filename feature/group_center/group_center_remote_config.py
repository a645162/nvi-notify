import json

import requests
from time import sleep as time_sleep

from feature.group_center.group_center import (
    access_key,
    group_center_get_url,
    group_center_login
)

from utils.logs import get_logger

logger = get_logger()

max_retry_times = 5


def get_json_str(target_api: str) -> str:
    url = group_center_get_url(target_api=target_api)

    for _ in range(max_retry_times):
        try:
            if access_key == "":
                group_center_login()

            params = {
                "accessKey": access_key
            }
            response = requests.get(
                url=url,
                params=params,
                timeout=10
            )

            text = response.text.strip()

            if response.status_code == 200:
                return text

            json_dict = json.loads(text)
            if (
                    isinstance(json_dict, dict) and
                    "isAuthenticated" in json_dict.keys() and
                    not json_dict["isAuthenticated"]
            ):
                logger.error(f"[Group Center]Not authorized")
                group_center_login()
        except Exception as e:
            logger.error("get user config json error", e)

        time_sleep(10)
    return ""


def get_user_config_json_str() -> str:
    return get_json_str(target_api="/api/client/config/user_list")


def init_remote_env_list():
    from config.settings import all_env_dict

    json_str = get_json_str(target_api="/api/client/config/env_list")

    env_dict = json.loads(json_str)
    if isinstance(env_dict, dict):
        print("-" * 20)
        print("Remote Env")
        for key in env_dict.keys():
            print(f"{key}: {env_dict[key]}")
        print("-" * 20)

        all_env_dict.update(env_dict)


if __name__ == "__main__":
    json_text = get_user_config_json_str()
    print(json_text)

    print()
