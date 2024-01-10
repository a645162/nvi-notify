import socket

from utils.env import *


def get_local_ip():
    try:
        # 获取主机名
        host_name = socket.gethostname()

        # 获取本地 IP 地址
        local_ip = socket.gethostbyname(host_name)

        return local_ip
    except Exception as e:
        print(f"Error: {e}")
        return None


def get_host_name():
    host_name = get_env("GPU_MONITOR_HOST_NAME", "")
    if host_name != "":
        return host_name

    try:
        # 获取主机名
        host_name = socket.gethostname()
        return host_name
    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == '__main__':
    # 获取并打印本地 IP 地址
    local_ip = get_local_ip()
    if local_ip:
        print(f"Your local IP address is: {local_ip}")
    else:
        print("Unable to retrieve local IP address.")
