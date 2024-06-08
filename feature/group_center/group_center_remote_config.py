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


def get_user_config_json_str() -> str:
    url = group_center_get_url(target_api="/api/client/config/user_list")

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

            json_dict = json.dumps(text)
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


if __name__ == "__main__":
    json_text = get_user_config_json_str()
    print(json_text)

    print()
