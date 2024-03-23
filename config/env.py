import os
from datetime import time


def get_env_str(key: str, default: str = None) -> str:
    if key in os.environ:
        return str(os.environ[key]).strip()
    return default


def get_env_int(key: str, default: int = None) -> int:
    str_int = get_env_str(key, "")
    try:
        return int(str_int)
    except:
        return default


def get_env_time(key: str, default: time = None) -> time:
    time_str = get_env_str(key, "")
    index = time_str.find(":")
    if index == -1:
        return default

    time_str_1 = time_str[:index].strip()
    time_str_2 = time_str[index + 1 :].strip()

    try:
        int_1 = int(time_str_1)
        int_2 = int(time_str_2)

        return time(int_1, int_2)
    except:
        return default


def get_env_variable(env_name: str) -> str:
    return get_env_str(env_name, "")


def get_env_variable_int(env_name: str) -> int:
    return get_env_int(env_name, -1)
