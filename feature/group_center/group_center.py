import json

import requests

from config.settings import get_settings
from utils.logs import get_logger
from utils.utils import get_md5_hash

logger = get_logger()
settings = get_settings()

def group_center_get_url(target_api: str):
    if settings.GROUP_CENTER_URL.endswith("/"):
        if target_api.startswith("/"):
            target_api = target_api[1:]
    else:
        if not target_api.startswith("/"):
            target_api = "/" + target_api

    return settings.GROUP_CENTER_URL + target_api


access_key = ""

group_center_public_part: dict = {
    "serverName": settings.SERVER_NAME,
    "serverNameEng": settings.SERVER_NAME_SHORT,
}


def __group_center_login(username: str, password: str) -> bool:
    logger.info("[Group Center] Login Start")
    url = group_center_get_url(target_api="/auth/client/auth")
    try:
        logger.info(f"[Group Center] Auth To: {url}")
        password_display = "*" * len(password)
        password_encoded = get_md5_hash(password)
        logger.info(
            f"[Group Center] Auth userName:{username} password:{password_display}"
        )

        response = requests.get(
            url=url,
            params={"userName": username, "password": password_encoded},
            timeout=10,
        )

        if response.status_code != 200:
            logger.error(f"[Group Center] Auth Failed: {response.text}")
            return False

        response_dict: dict = json.loads(response.text)
        if not (
            "isAuthenticated" in response_dict.keys()
            and response_dict["isAuthenticated"]
        ):
            logger.error("[Group Center] Not authorized")
            return False
        global access_key
        access_key = response_dict["accessKey"]
        logger.info(f"[Group Center] Auth Handshake Success: {access_key}")

    except Exception as e:
        logger.error(f"[Group Center] Auth Handshake Failed: {e}")
        return False

    logger.info("[Group Center] Login Finished.")


def group_center_login() -> bool:
    return __group_center_login(
        username=settings.SERVER_NAME_SHORT, password=settings.GROUP_CENTER_PASSWORD
    )
