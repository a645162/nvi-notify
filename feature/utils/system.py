import os
import sys


def check_is_linux() -> bool:
    return sys.platform == "linux"


def check_is_root() -> bool:
    return os.geteuid() == 0
