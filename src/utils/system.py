import os
import socket
import sys


def check_is_linux() -> bool:
    return sys.platform == "linux"


def check_is_root() -> bool:
    return os.geteuid() == 0


def is_port_in_use(host: str, port: int, *, proto: str = "tcp") -> bool:
    """检查 host:port 是否已被占用"""
    if proto == "tcp":
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:  # udp
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        s.bind((host, port))
        return False  # 绑定成功 → 端口空闲
    except OSError:
        return True  # Address already in use / Permission denied
    finally:
        s.close()
