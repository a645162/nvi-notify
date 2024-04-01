import glob
import os
import socket
from typing import Dict, List

import chardet
import psutil
import yaml

from utils.logs import get_logger

logger = get_logger()


def get_files_with_extension(
        directory: str, extension: str, recursive: bool = False
) -> List[str]:
    files = []
    if recursive:
        search_path = os.path.join(directory, f"**/*.{extension}")
    else:
        search_path = os.path.join(directory, f"*.{extension}")
    for file_path in glob.glob(search_path, recursive=recursive):
        files.append(os.path.abspath(file_path))
    return files


def parse_yaml(yaml_file_path: str) -> dict:
    # Check Encoding
    with open(yaml_file_path, "rb") as f:
        raw_data = f.read()
        result_encoding = chardet.detect(raw_data)
        encoding = result_encoding["encoding"]

        if encoding is None:
            encoding = "utf-8"

    file_content = raw_data.decode(encoding).strip()

    if len(file_content) == 0:
        return {}

    yaml_data = yaml.safe_load(file_content)

    return yaml_data


def get_interface_ip_dict(ip_type: str = "v4") -> Dict:
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


if __name__ == "__main__":
    # result = parse_yaml(os.path.join(os.getcwd(), "config/users/master/2023.yaml"))
    # print(result)

    files_list = get_files_with_extension("../../users", "yaml", True)

    # 打印文件列表
    for file_path in files_list:
        print(file_path)

    # ip_tpye = "v4"
    # interface_ip_dict = get_interface_ip_dict(ip_tpye)
    # print(interface_ip_dict)
