# -*- coding: utf-8 -*-
import datetime
import os
import platform
import socket
import sys
from typing import Dict

import psutil
from dotenv import dotenv_values, load_dotenv
from group_center.core import group_center_machine
from group_center.utils.log import logger as group_center_logger_utils
from nvitop import Device
from packaging import version

from config.user_info import UserInfo
from config.utils import get_users, set_iptables
from feature.monitor.monitor_enum import AllWebhookName
from feature.utils.logs import get_logger

logger = get_logger()

path_base = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class EnvironmentManager:
    all_env_dict: Dict[str, str] = {}

    @classmethod
    def load_env_file(
            cls, env_file: str, verbose: bool = True, override: bool = False
    ) -> Dict[str, str]:
        """Load environment variables from a file."""
        if os.path.exists(env_file):
            load_dotenv(env_file, verbose=verbose, override=override)
            return dotenv_values(env_file)
        logger.error(f"Env file not found: {env_file}")
        return {}

    @classmethod
    def load_env(cls):
        """Load environment variables from default and extended env files."""
        default_env_file = os.path.join(path_base, ".env")
        env_vars = cls.load_env_file(default_env_file)

        extend_env_file = os.path.join(
            os.getcwd(), ".env.dev" if sys.gettrace() else ".env.secure"
        )
        env_vars.update(cls.load_env_file(extend_env_file, override=True))

        cls.all_env_dict = env_vars

        logger.info("=" * 40)
        for env_name, env_value in env_vars.items():
            logger.info(f"{env_name}: {env_value}")
        logger.info("=" * 40)

    @classmethod
    def get(cls, key: str, default=None) -> str:
        if key in cls.all_env_dict:
            return str(cls.all_env_dict[key]).strip()

        return str(os.getenv(key, default)).strip()

    @classmethod
    def get_int(cls, key: str, default: int = 0) -> int:
        try:
            return int(cls.get(key, default))
        except Exception as e:
            logger.error(f"[var]{e}")
            return default

    @classmethod
    def get_bool(cls, key: str, default: bool = False) -> bool:
        assert isinstance(default, bool), logger.error(
            f'Env "{key}" default must be bool, but get {type(default)}'
        )

        value = cls.get(key, str(default))
        return value.strip().lower() == "true"

    @classmethod
    def get_time(cls, key: str, default: datetime.time) -> datetime.time:
        value = cls.get(key, "")
        try:
            return datetime.datetime.strptime(value, "%H:%M").time()
        except ValueError as e:
            logger.error(f"{e}")
            return default

    @classmethod
    def fix_url(cls, url: str) -> str:
        """Ensure the URL starts with http and ends with a slash."""
        if not url.startswith("http"):
            url = f"http://{url}"
        if not url.endswith("/"):
            url += "/"
        return url

    @classmethod
    def get_ip(cls, ip_type: str = "v4") -> str:
        assert ip_type in ["v4", "v6"]
        ip_dict = cls.get_interface_ip_dict(ip_type)
        for ip in ip_dict.values():
            return ip

    @classmethod
    def get_interface_ip_dict(cls, ip_type: str = "v4") -> dict:
        interface_ip_dict = {}
        family = socket.AF_INET if ip_type == "v4" else socket.AF_INET6

        # get local ip from dns
        try:
            if ip_type == "v4":
                s = socket.socket(family, socket.SOCK_DGRAM)
                s.connect(("114.114.114.114", 80))
            elif ip_type == "v6":
                s = socket.socket(family, socket.SOCK_DGRAM)
                s.connect(("6.ipw.cn", 80))
            local_ip = s.getsockname()[0]
        except Exception as e:
            logger.error(f"Error getting local IP: {e}")
            local_ip = None
        finally:
            s.close()

        interface_name_list = [
            interface_name.strip()
            for interface_name in psutil.net_if_addrs().keys()
            if interface_name.strip()
        ]

        # get local ip by psutil
        for interface_name in interface_name_list:
            for addr in psutil.net_if_addrs().get(interface_name, []):
                try:
                    if addr.family == family:
                        if ip_type == "v4":
                            socket.inet_aton(addr.address)
                        elif ip_type == "v6":
                            socket.inet_pton(family, addr.address)
                        if addr.address == local_ip:
                            interface_ip_dict[interface_name] = addr.address
                        break
                except socket.error:
                    pass
        return interface_ip_dict

    @staticmethod
    def check_sudo_permission() -> bool:
        # Check is Linux
        if platform.system() != "Linux":
            return False
        return os.geteuid() == 0

    @staticmethod
    def check_python_version(min_required_version: str) -> str:
        """
        Check if the current Python version is greater than or equal to the minimum required version.

        :param min_required_version: The minimum required Python version as a string.
        :return: True if the current Python version is greater than or equal to the minimum required version, False otherwise.
        """
        current_version = platform.python_version()

        assert version.parse(current_version) >= version.parse(
            min_required_version
        ), logger.error(
            "Python version must be greater than or equal to {}".format(
                min_required_version
            )
        )

        return current_version

    @staticmethod
    def now_time_str() -> str:
        """Get the current time as a formatted string."""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Load environment variables
EnvironmentManager.load_env()

# Init
WAIT_TIME_BEFORE_START = EnvironmentManager.get_int("WAIT_TIME_BEFORE_START", 10)
SUDO_PERMISSION = EnvironmentManager.check_sudo_permission()
PYTHON_VERSION = EnvironmentManager.check_python_version("3.10")

# Network
IPv4 = EnvironmentManager.get_ip("v4")
IPv6 = EnvironmentManager.get_ip("v6")

# GPU
NO_NVIDIA_GPU = EnvironmentManager.get_bool("NO_NVIDIA_GPU", False)
NUM_GPU = 0 if NO_NVIDIA_GPU else Device.count()

# Server Info
SERVER_NAME = EnvironmentManager.get("SERVER_NAME", "None")
SERVER_NAME_SHORT = EnvironmentManager.get("SERVER_NAME_SHORT", "")
SERVER_DOMAIN = EnvironmentManager.get("SERVER_DOMAIN", "None")

# Group Center
USE_GROUP_CENTER = EnvironmentManager.get_bool("USE_GROUP_CENTER", False)
GROUP_CENTER_URL = EnvironmentManager.get("GROUP_CENTER_URL", "http://localhost:8088")
GROUP_CENTER_PASSWORD = EnvironmentManager.get("GROUP_CENTER_PASSWORD", "password")

group_center_machine.set_group_center_host_url(GROUP_CENTER_URL)
group_center_machine.set_machine_name_full(SERVER_NAME)
group_center_machine.set_machine_name_short(SERVER_NAME_SHORT)
group_center_machine.set_machine_password(GROUP_CENTER_PASSWORD)
group_center_logger_utils.set_is_print_mode(is_print=False)
group_center_logger_utils.set_logger(logger)

ENV_FROM_GROUP_CENTER = \
    EnvironmentManager.get_bool("ENV_FROM_GROUP_CENTER", False)
if USE_GROUP_CENTER and ENV_FROM_GROUP_CENTER:
    from feature.group_center.group_center_remote_config import \
        init_remote_env_list

    init_remote_env_list()

# CPU Monitor
CPU_HIGH_TEMPERATURE_THRESHOLD = EnvironmentManager.get_int(
    "CPU_HIGH_TEMPERATURE_THRESHOLD", 85
)
TEMPERATURE_MONITOR_SAMPLING_INTERVAL = EnvironmentManager.get_int(
    "TEMPERATURE_MONITOR_SAMPLING_INTERVAL", 10
)

# GPU Monitor
GPU_MONITOR_SAMPLING_INTERVAL = EnvironmentManager.get_int(
    "GPU_MONITOR_SAMPLING_INTERVAL", 5
)
GPU_MONITOR_AUTO_RESTART = EnvironmentManager.get_bool("GPU_MONITOR_AUTO_RESTART", True)

# Hard Disk Monitor
HARD_DISK_MOUNT_POINT = set(
    m.strip() for m in EnvironmentManager.get("HARD_DISK_MOUNT_POINT", "/").split(",")
)
HARD_DISK_MONITOR_SAMPLING_INTERVAL = EnvironmentManager.get_int(
    "HARD_DISK_MONITOR_SAMPLING_INTERVAL", 3600
)
HARD_DISK_HIGH_PERCENTAGE_THRESHOLD = EnvironmentManager.get_int(
    "HARD_DISK_HIGH_PERCENTAGE_THRESHOLD", 95
)
HARD_DISK_LOW_FREE_GB_THRESHOLD = EnvironmentManager.get_int(
    "HARD_DISK_LOW_FREE_GB_THRESHOLD", 100
)

# Flask
FLASK_SERVER_HOST = EnvironmentManager.get("FLASK_SERVER_HOST", "0.0.0.0")
FLASK_SERVER_PORT = EnvironmentManager.get("FLASK_SERVER_PORT", "3000")
GPU_BOARD_WEB_URL = EnvironmentManager.get("GPU_BOARD_WEB_URL", "")

# WebHook
WEBHOOK_DELAY_SEND_SECONDS = EnvironmentManager.get_int(
    "WEBHOOK_DELAY_SEND_SECONDS", 60
)
WEBHOOK_SEND_LAUNCH_MESSAGE = EnvironmentManager.get_bool(
    "WEBHOOK_SEND_LAUNCH_MESSAGE", True
)
WEBHOOK_SLEEP_TIME_START = EnvironmentManager.get_time(
    "WEBHOOK_SLEEP_TIME_START", datetime.time(23, 0)
)
WEBHOOK_SLEEP_TIME_END = EnvironmentManager.get_time(
    "WEBHOOK_SLEEP_TIME_END", datetime.time(8, 0)
)

WEBHOOK_NAME = set(
    m.strip().upper()
    for m in EnvironmentManager.get("WEBHOOK_NAME", AllWebhookName.WEWORK.value).split(
        ","
    )
)
WEBHOOK_WEWORK_DEPLOY = EnvironmentManager.get("WEBHOOK_WEWORK_DEPLOY", "")
WEBHOOK_WEWORK_DEV = EnvironmentManager.get("WEBHOOK_WEWORK_DEV", "")
WEBHOOK_LARK_DEPLOY = EnvironmentManager.get("WEBHOOK_LARK_DEPLOY", "")
WEBHOOK_LARK_DEV = EnvironmentManager.get("WEBHOOK_LARK_DEV", "")

# User
USERS: Dict[str, UserInfo] = get_users()
if SUDO_PERMISSION:
    set_iptables(FLASK_SERVER_PORT)

# Fix URLs
GROUP_CENTER_URL = EnvironmentManager.fix_url(GROUP_CENTER_URL)
