# -*- coding: utf-8 -*-

import datetime
import os
import platform
import socket
import sys

import psutil
from dotenv import dotenv_values, load_dotenv
from nvitop import Device
from packaging import version

from config.user.user_info import UserInfo
from config.user.user_parser import UserConfigParser
from feature.monitor.cpu.cpu import CPUInfo
from feature.monitor.monitor_enum import AllWebhookName
from utils.logs import get_logger
from utils.utils import do_command

logger = get_logger()

path_base = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

all_env_dict: dict[str, str] = {}


class Settings:
    def __init__(self):
        self.load_env()

        # Network
        self.IPv4 = self.get_ip("v4")
        self.IPv6 = self.get_ip("v6")

        # CPU
        self.NUM_CPU = CPUInfo.get_cpu_num()

        # GPU

        self.NUM_GPU = Device.count()

        # Server Info
        self.SERVER_NAME = self.get_env_str("SERVER_NAME", "None")
        self.SERVER_NAME_SHORT = self.get_env_str("SERVER_NAME_SHORT", "")
        self.SERVER_DOMAIN = self.get_env_str("SERVER_DOMAIN", "None")

        # Group Center
        self.USE_GROUP_CENTER = self.get_bool_from_string(
            self.get_env_str("USE_GROUP_CENTER", "False")
        )
        self.GROUP_CENTER_URL = self.get_group_center_url()
        self.GROUP_CENTER_PASSWORD = self.get_env_str(
            "GROUP_CENTER_PASSWORD", "password"
        )

        self.ENV_FROM_GROUP_CENTER = (
            self.USE_GROUP_CENTER
            and self.get_bool_from_string(
                self.get_env_str("ENV_FROM_GROUP_CENTER", "False")
            )
        )
        if self.ENV_FROM_GROUP_CENTER:
            from feature.group_center.group_center_remote_config import \
                init_remote_env_list

            init_remote_env_list()

        # Init
        self.WAIT_TIME_BEFORE_START = int(
            self.get_env_int("WAIT_TIME_BEFORE_START", 10)
        )
        self.SUDO_PERMISSION = self.check_sudo_permission()
        self.PYTHON_VERSION = self.check_python_version("3.6")

        # CPU Monitor
        self.CPU_HIGH_TEMPERATURE_THRESHOLD = int(
            self.get_env_int("CPU_HIGH_TEMPERATURE_THRESHOLD", 85)
        )
        self.TEMPERATURE_MONITOR_SAMPLING_INTERVAL = int(
            self.get_env_int("TEMPERATURE_MONITOR_SAMPLING_INTERVAL", 300)
        )

        # GPU Monitor
        self.GPU_MONITOR_SAMPLING_INTERVAL = int(
            self.get_env_int("GPU_MONITOR_SAMPLING_INTERVAL", 5)
        )
        self.GPU_MONITOR_AUTO_RESTART = self.get_bool_from_string(
            self.get_env_str("GPU_MONITOR_AUTO_RESTART", "True").strip()
        )

        # Hard Disk Monitor
        self.HARD_DISK_MOUNT_POINT = set(
            m.strip() for m in self.get_env_str("HARD_DISK_MOUNT_POINT", "/").split(",")
        )
        self.HARD_DISK_MONITOR_SAMPLING_INTERVAL = int(
            self.get_env_int("HARD_DISK_MONITOR_SAMPLING_INTERVAL", 3600)
        )
        self.HARD_DISK_HIGH_PERCENTAGE_THRESHOLD = int(
            self.get_env_int("HARD_DISK_HIGH_PERCENTAGE_THRESHOLD", 95)
        )
        self.HARD_DISK_LOW_FREE_GB_THRESHOLD = int(
            self.get_env_int("HARD_DISK_LOW_FREE_GB_THRESHOLD", 100)
        )

        # Flask
        self.FLASK_SERVER_HOST = self.get_env_str("FLASK_SERVER_HOST", "0.0.0.0")
        self.FLASK_SERVER_PORT = self.get_env_str("FLASK_SERVER_PORT", "3000")
        self.GPU_BOARD_WEB_URL = self.get_env_str("GPU_BOARD_WEB_URL", "")

        # WebHook
        self.WEBHOOK_DELAY_SEND_SECONDS = int(
            self.get_env_int("WEBHOOK_DELAY_SEND_SECONDS", 60)
        )
        self.WEBHOOK_SEND_LAUNCH_MESSAGE = self.get_bool_from_string(
            self.get_env_str("WEBHOOK_SEND_LAUNCH_MESSAGE", "True")
        )

        self.WEBHOOK_NAME = set(
            m.strip().upper()
            for m in self.get_env_str(
                "WEBHOOK_NAME", AllWebhookName.WEWORK.value
            ).split(",")
        )
        self.WEBHOOK_WEWORK_DEPLOY = self.get_env_str(
            "WEBHOOK_WEWORK_DEPLOY", ""
        ).strip()
        self.WEBHOOK_WEWORK_DEV = self.get_env_str("WEBHOOK_WEWORK_DEV", "").strip()

        self.WEBHOOK_LARK_DEPLOY = self.get_env_str("WEBHOOK_LARK_DEPLOY", "").strip()
        self.WEBHOOK_LARK_DEV = self.get_env_str("WEBHOOK_LARK_DEV", "").strip()

        # User
        self.USERS: dict[str, UserInfo] = self.get_users()

        if self.SUDO_PERMISSION:
            self.set_iptables(self.FLASK_SERVER_PORT)

    @property
    def is_webhook_sleep_time(self) -> bool:
        sleep_time_start = self.get_env_time(
            self.get_env_str("WEBHOOK_SLEEP_TIME_START", "23:00"), datetime.time(23, 0)
        )
        sleep_time_end = self.get_env_time(
            self.get_env_str("WEBHOOK_SLEEP_TIME_END", "08:00"), datetime.time(8, 0)
        )
        if self.is_within_time_range(sleep_time_start, sleep_time_end):
            return True
        else:
            return False

    def get_group_center_url(self):
        group_center_url = self.get_env_str("GROUP_CENTER_URL", "http://localhost:8088")
        if not group_center_url.startswith("http"):
            group_center_url = f"http://{group_center_url}"

        if not group_center_url.endswith("/"):
            group_center_url += "/"

        return group_center_url

    def get_users(self):
        users_obj_dict: dict[str, UserInfo] = {}
        user_config_parser = UserConfigParser()

        user_from_group_center = self.USE_GROUP_CENTER and self.get_bool_from_string(
            self.get_env_str("USER_FROM_GROUP_CENTER", "False")
        )
        user_from_local_files = self.get_bool_from_string(
            self.get_env_str("USER_FROM_LOCAL_FILES", "True")
        )

        if user_from_local_files:
            user_list_from_files = (
                user_config_parser.get_user_info_by_yaml_from_directory(
                    os.path.join(os.getcwd(), "config/users")
                )
            )
            logger.info(f"User count from file: {len(user_list_from_files)}")
            users_obj_dict.update(user_list_from_files)
        if user_from_group_center:
            user_list_from_group_center = (
                user_config_parser.get_json_user_config_from_group_center()
            )
            logger.info(
                f"User count from Group Center: {len(user_list_from_group_center)}"
            )
            users_obj_dict.update(user_list_from_group_center)

        logger.info(f"Final user count: {len(users_obj_dict)}")

        return users_obj_dict

    def get_ip(self, ip_type: str = "v4") -> str:
        assert ip_type in ["v4", "v6"]
        ip_dict = self.get_interface_ip_dict(ip_type)
        for ip in ip_dict.values():
            return ip

    @staticmethod
    def load_env():
        default_env_file = os.path.join(path_base, ".env")

        if os.path.exists(default_env_file):
            load_dotenv(default_env_file, verbose=True)
            env_vars = dotenv_values(default_env_file)
        else:
            logger.error("default env file not found")
            return

        if sys.gettrace():
            extend_env_file = os.path.join(os.getcwd(), ".env.dev")
        else:
            extend_env_file = os.path.join(os.getcwd(), ".env.secure")

        if os.path.exists(extend_env_file):
            new_env_vars = dotenv_values(extend_env_file)
            load_dotenv(extend_env_file, verbose=True, override=True)
            env_vars.update(new_env_vars)

        logger.info("=" * 40)
        for env_name, env in env_vars.items():
            logger.info(f"{env_name}: {env}")
        logger.info("=" * 40)

    @staticmethod
    def get_env_str(var: str, default: str) -> str:
        global all_env_dict

        if var in all_env_dict:
            return all_env_dict[var]

        return os.getenv(var, default)

    @staticmethod
    def get_bool_from_string(value: str) -> bool:
        return value.strip().lower() == "true"

    @staticmethod
    def get_env_int(var: str, default: int) -> int:
        try:
            return int(os.getenv(var))
        except Exception as e:
            logger.error(f"[var]{e}")
            return default

    @staticmethod
    def get_env_time(value: str, default: datetime.time) -> datetime.time:
        try:
            return datetime.datetime.strptime(value, "%H:%M").time()
        except ValueError as e:
            logger.error(f"{e}")
            return default

    @staticmethod
    def check_sudo_permission() -> bool:
        return os.geteuid() == 0

    @staticmethod
    def check_python_version(min_required_version: str) -> bool:
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
    def get_interface_ip_dict(ip_type: str = "v4") -> dict:
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

    @property
    def now_time_str(self) -> str:
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

        return formatted_time

    @staticmethod
    def is_within_time_range(
        start_time=datetime.time(11, 0), end_time=datetime.time(7, 30)
    ) -> bool:
        current_time = datetime.datetime.now().time()

        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:
            return start_time <= current_time or current_time <= end_time

    @staticmethod
    def set_iptables(port: str) -> None:
        cmd_list = [
            f"sudo iptables -I INPUT -p tcp --dport {port} -j ACCEPT",
            f"sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port {port}",
            f"sudo ip6tables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port {port}",
        ]
        for cmd in cmd_list:
            try:
                do_command(cmd)
            except Exception as e:
                logger.warning(f"Set iptables error: {e} when executing {cmd}")

        logger.info("Set iptables success!")


settings = Settings()


def get_settings() -> Settings:
    return settings


if __name__ == "__main__":
    load_dotenv(dotenv_path="", verbose=True)
