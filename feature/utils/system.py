import os
import sys

from feature.utils.common_utils import cat_info


def check_is_linux() -> bool:
    return sys.platform == 'linux'


def check_is_root() -> bool:
    return os.geteuid() == 0


def get_os_release_id():
    for line in cat_info('/etc/os-release').strip().split("\n"):
        key, value = line.rstrip().split('=', 1)
        if key =="ID":
            return value.strip('"')
