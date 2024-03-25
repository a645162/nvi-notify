import os
import socket
from typing import List, Union

import psutil


# Get IP address of network interface
def get_ip_address(interface_name, ip_type: str) -> str:
    try:
        address_list = psutil.net_if_addrs()[interface_name]
        if ip_type == "v4":
            ip_address = next(
                addr.address for addr in address_list if addr.family == socket.AF_INET
            )
        elif ip_type == "v6":
            ip_address = next(
                addr.address for addr in address_list if addr.family == socket.AF_INET6
            )
        return str(ip_address).strip()
    except (KeyError, StopIteration):
        return ""


# Get all network interface names
def get_interface_name_list(black_list=None) -> List[str]:
    if black_list is None:
        black_list = []

    return [
        interface_name.strip()
        for interface_name in psutil.net_if_addrs().keys()
        if len(interface_name.strip()) > 0
        and not is_text_in_black_list(interface_name, black_list)
    ]


def get_black_list(black_list_txt_path: str = None) -> List[str]:
    if black_list_txt_path is None:
        current_directory = os.path.dirname(os.path.abspath(__file__))
        black_list_txt_path = os.path.join(current_directory, "black_list.txt")
    if not os.path.exists(black_list_txt_path):
        return []
    with open(black_list_txt_path, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f.readlines() if len(line.strip()) > 0]


def is_text_in_black_list(text: str, black_list: List[str]) -> bool:
    for black_list_str in black_list:
        if text.lower().find(black_list_str) != -1:
            print(f"[{text}] in black list")
            return True
    return False


def is_valid_ip_address(ip_address: str, ip_type: str) -> bool:
    try:
        if ip_type == "v4":
            socket.inet_aton(ip_address)
        elif ip_type == "v6":
            socket.inet_pton(socket.AF_INET6, ip_address)
        return True
    except socket.error:
        return False


def get_valid_ip_list(
    interface_name_list: List[str] = None,
    black_list: List[str] = None,
    ip_type: str = "v4",
) -> List[str]:
    if interface_name_list is None:
        if black_list is None:
            black_list = get_black_list()
        interface_name_list = get_interface_name_list(black_list=black_list)

    ip_list = []
    for interface_name in interface_name_list:
        ip_addr = get_ip_address(interface_name, ip_type)
        if is_valid_ip_address(ip_addr, ip_type):
            ip_list.append(ip_addr)

    return ip_list


def get_list_diff(list1: List[str], list2: List[str]) -> List[str]:
    return list(set(list1).symmetric_difference(set(list2)))


def get_ip_change(
    last_ip_list: List[str], current_ip_list: List[str]
) -> Union[List[str], List[str]]:
    diff_list = get_list_diff(last_ip_list, current_ip_list)
    if len(diff_list) == 0:
        return [], []

    disabled_ip_list = []
    new_ip_list = []

    for diff_ip in diff_list:
        if diff_ip in last_ip_list:
            disabled_ip_list.append(diff_ip)
        else:
            new_ip_list.append(diff_ip)

    return disabled_ip_list, new_ip_list


def get_local_ip_from_dns(ip_type: str):
    try:
        if ip_type == "v4":
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("114.114.114.114", 80))
        elif ip_type == "v6":
            s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            s.connect(("6.ipw.cn", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return None


def get_local_ip(ip_type: str):
    """
    Args:
        ip_type (str): choices: ["v4", "v6"]

    Returns:
        ip (str): local ip
    """
    black_list = get_black_list("config/network_interface_black_list.txt")
    interface_name_list = get_interface_name_list(black_list=black_list)

    ip_list = get_valid_ip_list(
        interface_name_list=interface_name_list, black_list=black_list, ip_type=ip_type
    )
    for ip in ip_list:
        if ip == get_local_ip_from_dns(ip_type):
            return ip


if __name__ == "__main__":
    black_list = get_black_list()
    print(black_list)
    interface_name_list = get_interface_name_list(black_list=black_list)
    print(interface_name_list)

    ip = get_valid_ip_list(
        interface_name_list=interface_name_list, black_list=black_list
    )
    print(ip)
    for i in ip:
        print(i)
        if i == get_local_ip_from_dns():
            print(11111)
