import os
import sys


def check_is_linux() -> bool:
    return sys.platform == 'linux'


def check_is_sudo() -> bool:
    return os.geteuid() == 0

# alias
check_is_root = check_is_sudo
