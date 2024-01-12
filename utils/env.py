import os
from datetime import time


def get_env(key, default=None):
    if key in os.environ:
        return str(os.environ[key]).strip()
    return default


def get_env_int(key, default=None):
    str_int = get_env(key, "")
    try:
        return int(str_int)
    except:
        return default


def get_env_time(key, default=None):
    time_str = get_env(key, "")
    index = time_str.find(":")
    if index == -1:
        return default

    time_str_1 = time_str[:index].strip()
    time_str_2 = time_str[index + 1:].strip()

    try:
        int_1 = int(time_str_1)
        int_2 = int(time_str_2)

        return time(int_1, int_2)
    except:
        return default


def get_env_variable(env_name):
    # 使用 os.environ.get 获取环境变量的值
    env_value = os.environ.get(env_name)

    # 如果环境变量不存在或为空，返回空字符串
    return env_value.strip() if env_value is not None else ""


def get_env_variable_int(env_name):
    env_str = get_env_variable(env_name)
    if env_str == "":
        return -1
    else:
        value: int
        try:
            value = int(env_str)
        except:
            value = -1
        return value
