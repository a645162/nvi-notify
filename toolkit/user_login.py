"""
用户最后登录时间查询工具类

提供以下功能：
1. 查询用户最后一次"真实登录会话"的时间（SSH、本地终端、su – 等）
2. 查询用户最后一次"出现在系统里"的时间（只要曾经登录过就会写，不管是否成功）
3. 一次性扫描所有用户
4. 过滤系统内置用户

使用要求：
- 需要root权限执行（因为日志文件需要root权限读取）
- Linux系统

使用示例：
    # 基本使用
    from toolkit.user_login import UserLoginChecker, get_user_lastlog

    # 查询单个用户
    info = get_user_lastlog('konghaomin')
    print(f'最后登录: {info.login_time}')

    # 查询所有用户（排除系统用户）
    checker = UserLoginChecker(exclude_system_users=True)
    all_users = checker.get_all_users_lastlog()

    # 自定义排除用户列表
    custom_exclude = {'test_user', 'temp_user'}
    checker = UserLoginChecker(
        exclude_system_users=True,
        custom_exclude_users=custom_exclude
    )

    # 访问预设的系统用户清单
    from toolkit.user_login import DEFAULT_SYSTEM_USERS
    print(f'系统用户数量: {len(DEFAULT_SYSTEM_USERS)}')

    # 检查用户是否为系统用户
    checker = UserLoginChecker()
    if checker.is_system_user('daemon'):
        print('daemon 是系统用户')

命令行使用：
    # 查询所有用户
    python user_login.py

    # 查询所有用户（排除系统用户）
    python user_login.py -s
    python user_login.py --no-system

    # 查询特定用户
    python user_login.py konghaomin

    # 显示帮助
    python user_login.py --help
"""

import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

# 系统内置用户过滤清单
# 这些用户通常是系统服务账户，不是真实的人类用户
DEFAULT_SYSTEM_USERS: Set[str] = {
    # 传统 Unix 系统用户
    "daemon",
    "bin",
    "sys",
    "sync",
    "games",
    "man",
    "lp",
    "mail",
    "news",
    "uucp",
    "proxy",
    "nobody",
    # 服务用户
    "www-data",
    "backup",
    "list",
    "irc",
    "sshd",
    # 包管理和系统服务
    "_apt",
    "_flatpak",
    # systemd 相关
    "systemd-network",
    "systemd-timesync",
    "systemd-resolve",
    "systemd-oom",
    # 网络服务
    "dhcpcd",
    "messagebus",
    "dnsmasq",
    "avahi",
    "nm-openvpn",
    # 日志和监控
    "syslog",
    "kernoops",
    "whoopsie",
    # 设备和硬件
    "uuidd",
    "usbmux",
    "tss",
    "tcpdump",
    # 打印和扫描
    "cups-pk-helper",
    "cups-browsed",
    "hplip",
    "saned",
    # 桌面环境
    "speech-dispatcher",
    "polkitd",
    "rtkit",
    "colord",
    "gnome-initial-set",
    "gdm",
    "gnome-remote-desk",
    "geoclue",
    # 其他服务
    "sssd",
    "fwupd-refresh",
    # 应用服务账户（可能需要根据实际情况调整）
    "nvidia-persistenc",  # NVIDIA 持久化守护进程
    "ollama",  # Ollama AI 服务
}


@dataclass
class LastLoginInfo:
    """最后登录信息"""

    username: str
    login_time: Optional[datetime]  # 最后登录时间
    login_type: str  # 登录类型（SSH/本地终端等）
    from_host: str  # 登录来源
    duration: str  # 登录持续时间
    raw_output: str  # 原始输出
    port: str = ""  # 登录端口（如 pts/0, pts/1 等）
    is_never_logged_in: bool = False  # 是否从未登录过


class UserLoginChecker:
    """用户最后登录时间检查器"""

    def __init__(
        self,
        sudo: bool = False,
        exclude_system_users: bool = False,
        custom_exclude_users: Optional[Set[str]] = None,
    ):
        """
        初始化检查器

        Args:
            sudo: 是否使用sudo以root身份执行命令
            exclude_system_users: 是否排除系统内置用户
            custom_exclude_users: 自定义要排除的用户集合（会与默认系统用户合并）
        """
        self.sudo = sudo
        self.exclude_system_users = exclude_system_users

        # 构建排除用户集合
        self.excluded_users: Set[str] = set()
        if exclude_system_users:
            self.excluded_users.update(DEFAULT_SYSTEM_USERS)
        if custom_exclude_users:
            self.excluded_users.update(custom_exclude_users)

        self._last_command = self._build_command("last")
        self._lastlog_command = self._build_command("lastlog")

    def _build_command(self, base_command: str) -> List[str]:
        """构建命令，支持sudo"""
        if self.sudo:
            return ["sudo", "-n", base_command]
        return [base_command]

    def _execute_command(self, cmd: List[str], timeout: int = 10) -> tuple:
        """
        执行命令并返回结果

        Returns:
            tuple: (returncode, stdout, stderr)
        """
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)

    def _parse_last_output(self, output: str, username: str) -> LastLoginInfo:
        """
        解析last命令输出

        last命令输出格式：
        username pts/0 192.168.1.10 Mon Dec 25 14:32 - 14:45 (00:13)

        Returns:
            LastLoginInfo: 解析后的登录信息
        """
        lines = output.strip().split("\n")
        if not lines or lines[0] == "":
            return LastLoginInfo(
                username=username,
                login_time=None,
                login_type="",
                from_host="",
                duration="",
                raw_output=output,
                port="",
                is_never_logged_in=True,
            )

        # 取第一行（最新的登录记录）
        first_line = lines[0]

        login_type = ""
        from_host = ""
        duration = ""
        login_time = None

        # 先提取基本字段：username pts/0 192.168.1.10 ...
        parts = first_line.split()
        if len(parts) >= 3:
            login_type = parts[1]  # pts/0
            from_host = parts[2]  # 192.168.1.10

        # 解析时间部分 - 使用正则表达式匹配整行
        # 完整格式：username pts/0 192.168.1.10 Mon Dec 25 14:32 - 14:45 (00:13)
        # 时间部分：Mon Dec 25 14:32 - 14:45 (00:13)
        time_pattern = (
            r"(\w+)\s+(\w+)\s+(\d+)\s+(\d+:\d+)\s+-\s+(\d+:\d+)\s+\((\d+:\d+)\)"
        )
        match = re.search(time_pattern, first_line)

        if match:
            weekday, month, day, start_time, end_time, duration_str = match.groups()
            duration = duration_str
            time_str = f"{month} {day} {start_time}"
            try:
                # 获取当前年份
                current_year = datetime.now().year
                time_str_full = f"{time_str} {current_year}"
                login_time = datetime.strptime(time_str_full, "%b %d %H:%M %Y")

                # 检查是否跨年（如果解析的日期在未来，说明应该是去年的）
                if login_time > datetime.now():
                    time_str_full = f"{time_str} {current_year - 1}"
                    login_time = datetime.strptime(time_str_full, "%b %d %H:%M %Y")
            except ValueError:
                pass

        return LastLoginInfo(
            username=username,
            login_time=login_time,
            login_type=login_type,
            from_host=from_host,
            duration=duration,
            raw_output=output,
            port="",
            is_never_logged_in=False,
        )

    def _parse_lastlog_output(self, output: str, username: str) -> LastLoginInfo:
        """
        解析lastlog命令输出

        lastlog 使用固定列宽格式：
        - 列1 (0-16): 用户名
        - 列2 (17-25): 端口
        - 列3 (26-42): 来源
        - 列4 (43-): 最后登录时间

        Returns:
            LastLoginInfo: 解析后的登录信息
        """
        lines = output.strip().split("\n")

        # 检查是否从未登录过
        if len(lines) == 1 or "Never logged in" in output or "从未登录" in output:
            return LastLoginInfo(
                username=username,
                login_time=None,
                login_type="",
                from_host="",
                duration="",
                raw_output=output,
                port="",
                is_never_logged_in=True,
            )

        # 取数据行（跳过标题行）
        if len(lines) >= 2:
            data_line = lines[1]
        else:
            data_line = lines[0]

        # 检查是否从未登录
        if (
            "Never logged in" in data_line
            or "**Never logged in**" in data_line
            or "从未登录" in data_line
        ):
            return LastLoginInfo(
                username=username,
                login_time=None,
                login_type="",
                from_host="",
                duration="",
                raw_output=output,
                port="",
                is_never_logged_in=True,
            )

        # 按列位置提取字段（lastlog 使用固定列宽）
        from_host = data_line[26:43].strip() if len(data_line) > 26 else ""
        time_str = data_line[43:].strip() if len(data_line) > 43 else ""

        login_time = None

        # 尝试解析时间
        if time_str:
            # 尝试常见格式
            formats_to_try = [
                "%a %b %d %H:%M:%S %z %Y",  # 英文：Sun Dec 28 00:40:01 +0800 2023
                "%a %m月 %d %H:%M:%S %z %Y",  # 中文：日 12月 28 00:40:01 +0800 2025
            ]

            for fmt in formats_to_try:
                try:
                    login_time = datetime.strptime(time_str, fmt)
                    break
                except ValueError:
                    continue

            # 如果还是失败，尝试正则
            if login_time is None:
                time_pattern = (
                    r"\w+\s+(\w+|\d+月)\s+(\d+)\s+(\d+:\d+:\d+)\s+[+-]\d+\s+(\d+)"
                )
                match = re.search(time_pattern, time_str)
                if match:
                    month_part, day, time_part, year = match.groups()
                    if "月" in month_part:
                        month_part = month_part.replace("月", "")
                        month_map = {
                            "1": "Jan",
                            "2": "Feb",
                            "3": "Mar",
                            "4": "Apr",
                            "5": "May",
                            "6": "Jun",
                            "7": "Jul",
                            "8": "Aug",
                            "9": "Sep",
                            "10": "Oct",
                            "11": "Nov",
                            "12": "Dec",
                        }
                        month_part = month_map.get(month_part, month_part)

                    datetime_str = f"{month_part} {day} {time_part} {year}"
                    try:
                        login_time = datetime.strptime(
                            datetime_str, "%b %d %H:%M:%S %Y"
                        )
                    except ValueError:
                        try:
                            login_time = datetime.strptime(
                                datetime_str, "%B %d %H:%M:%S %Y"
                            )
                        except ValueError:
                            pass

        return LastLoginInfo(
            username=username,
            login_time=login_time,
            login_type="lastlog",
            from_host=from_host,
            duration="",
            raw_output=output,
            is_never_logged_in=login_time is None,
        )

    def get_last_login_by_last(self, username: str) -> LastLoginInfo:
        """
        使用last命令查询用户最后一次真实登录会话的时间

        Args:
            username: 用户名

        Returns:
            LastLoginInfo: 最后登录信息
        """
        cmd = self._last_command + ["-1", username]
        returncode, stdout, stderr = self._execute_command(cmd)

        if returncode != 0:
            # 命令执行失败
            return LastLoginInfo(
                username=username,
                login_time=None,
                login_type="",
                from_host="",
                duration="",
                raw_output=stderr,
                port="",
                is_never_logged_in=True,
            )

        return self._parse_last_output(stdout, username)

    def get_last_login_by_lastlog(self, username: str) -> LastLoginInfo:
        """
        使用lastlog命令查询用户最后一次出现在系统里的时间

        Args:
            username: 用户名

        Returns:
            LastLoginInfo: 最后登录信息
        """
        cmd = self._lastlog_command + ["-u", username]
        returncode, stdout, stderr = self._execute_command(cmd)

        if returncode != 0:
            return LastLoginInfo(
                username=username,
                login_time=None,
                login_type="",
                from_host="",
                duration="",
                raw_output=stderr,
                port="",
                is_never_logged_in=True,
            )

        return self._parse_lastlog_output(stdout, username)

    def get_all_users_lastlog(self, days: Optional[int] = None) -> List[LastLoginInfo]:
        """
        扫描所有用户的最后登录时间

        Args:
            days: 如果指定，只返回最近days天内有登录的用户

        Returns:
            List[LastLoginInfo]: 所有用户的最后登录信息列表
        """
        cmd = self._lastlog_command[:]  # 复制命令列表
        if days is not None:
            cmd.extend(["-t", str(days)])

        returncode, stdout, stderr = self._execute_command(cmd)

        if returncode != 0:
            return []

        all_users = self._parse_all_lastlog_output(stdout)

        # 如果需要过滤系统用户
        if self.exclude_system_users or self.excluded_users:
            all_users = [u for u in all_users if u.username not in self.excluded_users]

        return all_users

    def is_system_user(self, username: str) -> bool:
        """
        判断用户是否为系统用户

        Args:
            username: 用户名

        Returns:
            bool: 是否为系统用户
        """
        return username in DEFAULT_SYSTEM_USERS

    def _parse_all_lastlog_output(self, output: str) -> List[LastLoginInfo]:
        """
        解析所有用户的lastlog输出

        lastlog 使用固定列宽格式：
        - 列1 (0-16): 用户名
        - 列2 (17-25): 端口
        - 列3 (26-42): 来源
        - 列4 (43-): 最后登录时间

        Args:
            output: lastlog命令的完整输出

        Returns:
            List[LastLoginInfo]: 所有用户的登录信息列表
        """
        result = []
        lines = output.strip().split("\n")

        if len(lines) <= 1:
            return result

        # 跳过标题行
        data_lines = lines[1:]

        for line in data_lines:
            if not line.strip():
                continue

            # 按列位置提取字段（lastlog 使用固定列宽）
            # 用户名通常在前17个字符，端口在17-25，来源在26-42，时间在43之后
            username = line[:17].strip() if len(line) > 0 else ""
            port = line[17:26].strip() if len(line) > 17 else ""
            from_host = line[26:43].strip() if len(line) > 26 else ""
            time_str = line[43:].strip() if len(line) > 43 else ""

            # 检查是否从未登录
            if (
                "从未登录" in time_str
                or "Never logged in" in time_str
                or "**从未登录过**" in time_str
                or "**Never logged in**" in time_str
            ):
                result.append(
                    LastLoginInfo(
                        username=username,
                        login_time=None,
                        login_type="",
                        from_host="",
                        duration="",
                        raw_output=line,
                        port="",
                        is_never_logged_in=True,
                    )
                )
                continue

            # 解析时间
            login_time = None
            if time_str:
                # 尝试常见格式
                formats_to_try = [
                    "%a %b %d %H:%M:%S %z %Y",  # 英文：Sun Dec 28 00:40:01 +0800 2023
                    "%a %m月 %d %H:%M:%S %z %Y",  # 中文：日 12月 28 00:40:01 +0800 2025
                ]

                for fmt in formats_to_try:
                    try:
                        login_time = datetime.strptime(time_str, fmt)
                        break
                    except ValueError:
                        continue

                # 如果还是失败，尝试正则
                if login_time is None:
                    time_pattern = (
                        r"\w+\s+(\w+|\d+月)\s+(\d+)\s+(\d+:\d+:\d+)\s+[+-]\d+\s+(\d+)"
                    )
                    match = re.search(time_pattern, time_str)
                    if match:
                        month_part, day, time_part, year = match.groups()
                        if "月" in month_part:
                            month_part = month_part.replace("月", "")
                            month_map = {
                                "1": "Jan",
                                "2": "Feb",
                                "3": "Mar",
                                "4": "Apr",
                                "5": "May",
                                "6": "Jun",
                                "7": "Jul",
                                "8": "Aug",
                                "9": "Sep",
                                "10": "Oct",
                                "11": "Nov",
                                "12": "Dec",
                            }
                            month_part = month_map.get(month_part, month_part)

                        datetime_str = f"{month_part} {day} {time_part} {year}"
                        try:
                            login_time = datetime.strptime(
                                datetime_str, "%b %d %H:%M:%S %Y"
                            )
                        except ValueError:
                            pass

            info = LastLoginInfo(
                username=username,
                login_time=login_time,
                login_type="lastlog",
                from_host=from_host,
                duration="",
                raw_output=line,
                port=port,
                is_never_logged_in=login_time is None,
            )
            result.append(info)

        return result

    def get_user_login_info(
        self, username: str, use_both: bool = True
    ) -> Dict[str, Any]:
        """
        获取用户的完整登录信息

        Args:
            username: 用户名
            use_both: 是否同时查询last和lastlog

        Returns:
            Dict[str, Any]: 包含两种查询结果的字典
        """
        last_info = self.get_last_login_by_last(username)
        lastlog_info = self.get_last_login_by_lastlog(username)

        result = {
            "username": username,
            "last_login": {
                "time": last_info.login_time,
                "type": last_info.login_type,
                "from": last_info.from_host,
                "duration": last_info.duration,
                "is_never": last_info.is_never_logged_in,
            },
            "lastlog": {
                "time": lastlog_info.login_time,
                "from": lastlog_info.from_host,
                "is_never": lastlog_info.is_never_logged_in,
            },
        }

        if not use_both:
            # 只返回lastlog的结果（更可靠，始终保留最后一次）
            result["primary"] = result["lastlog"]
        else:
            # last显示的是"真实登录会话"，lastlog显示的是"最后一次出现"
            # 通常lastlog的结果更全面
            result["primary"] = result["lastlog"]

        return result


def get_user_last_login(username: str, sudo: bool = False) -> LastLoginInfo:
    """
    便捷函数：查询用户最后一次真实登录会话的时间

    Args:
        username: 用户名
        sudo: 是否使用sudo

    Returns:
        LastLoginInfo: 最后登录信息
    """
    checker = UserLoginChecker(sudo=sudo)
    return checker.get_last_login_by_last(username)


def get_user_lastlog(username: str, sudo: bool = False) -> LastLoginInfo:
    """
    便捷函数：查询用户最后一次出现在系统里的时间

    Args:
        username: 用户名
        sudo: 是否使用sudo

    Returns:
        LastLoginInfo: 最后登录信息
    """
    checker = UserLoginChecker(sudo=sudo)
    return checker.get_last_login_by_lastlog(username)


def get_all_users_login_info(
    days: Optional[int] = None, sudo: bool = False, exclude_system_users: bool = False
) -> List[LastLoginInfo]:
    """
    便捷函数：扫描所有用户的最后登录时间

    Args:
        days: 如果指定，只返回最近days天内有登录的用户
        sudo: 是否使用sudo
        exclude_system_users: 是否排除系统内置用户

    Returns:
        List[LastLoginInfo]: 所有用户的登录信息列表
    """
    checker = UserLoginChecker(sudo=sudo, exclude_system_users=exclude_system_users)
    return checker.get_all_users_lastlog(days=days)


if __name__ == "__main__":
    # 直接运行时演示
    import sys

    print("=== 用户最后登录时间查询工具 ===")
    print()

    # 检查是否以root身份运行
    if os.geteuid() != 0:
        print("警告：当前不是以root身份运行，可能无法查询其他用户的登录信息")
        print("建议使用 sudo 运行或设置 sudo=True")
        print()

    # 解析命令行参数
    exclude_system = "--no-system" in sys.argv or "-s" in sys.argv
    show_help = "--help" in sys.argv or "-h" in sys.argv

    if show_help:
        print("使用方法:")
        print("  python user_login.py [选项] [用户名]")
        print()
        print("选项:")
        print("  -s, --no-system    排除系统内置用户")
        print("  -h, --help         显示此帮助信息")
        print()
        print("示例:")
        print("  python user_login.py                    # 查询所有用户")
        print(
            "  python user_login.py -s                 # 查询所有用户（排除系统用户）"
        )
        print("  python user_login.py konghaomin         # 查询特定用户")
        print()
        print(f"当前预设的系统用户数量: {len(DEFAULT_SYSTEM_USERS)}")
        print("可以通过 custom_exclude_users 参数添加自定义排除用户")
        sys.exit(0)

    # 移除选项参数，保留用户名参数
    args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]

    checker = UserLoginChecker(sudo=False, exclude_system_users=exclude_system)

    if len(args) > 0:
        # 命令行参数指定用户名
        username = args[0]
        print(f"查询用户: {username}")

        # 检查是否为系统用户
        if checker.is_system_user(username):
            print(f"  (提示: {username} 是预设的系统内置用户)")
        print("-" * 50)

        info = checker.get_user_login_info(username)
        print("Last命令结果（真实登录会话）:")
        print(f"  登录时间: {info['last_login']['time']}")
        print(f"  登录类型: {info['last_login']['type']}")
        print(f"  登录来源: {info['last_login']['from']}")
        print(f"  持续时间: {info['last_login']['duration']}")
        print(f"  从未登录: {info['last_login']['is_never']}")
        print()
        print("Lastlog命令结果（系统出现）:")
        print(f"  最后出现: {info['lastlog']['time']}")
        print(f"  来源: {info['lastlog']['from']}")
        print(f"  从未登录: {info['lastlog']['is_never']}")
    else:
        # 查询所有用户
        if exclude_system:
            print("查询所有用户（已排除系统用户）...")
            print(f"已排除 {len(DEFAULT_SYSTEM_USERS)} 个预设系统用户")
        else:
            print("查询所有用户...")
            print("提示: 使用 -s 或 --no-system 参数可排除系统用户")
        print()

        all_users = checker.get_all_users_lastlog()

        for user_info in all_users:
            status = (
                "从未登录"
                if user_info.is_never_logged_in
                else str(user_info.login_time)
            )
            print(f"{user_info.username}: {status} (来源: {user_info.from_host})")
