import os
import sys
from typing import List

import psutil


def is_debug_mode() -> bool:
    """
    Check if the current environment is in debug mode.

    Returns:
        bool: True if in debug mode, False otherwise.
    """

    if is_run_by_screen():
        return False

    if sys.gettrace():
        return True

    if is_run_by_gateway() or is_run_by_vscode_remote():
        return True

    debug_str = os.getenv("DEBUG")
    if debug_str is None:
        debug_str = ""

    return debug_str.lower() == "true" or debug_str == "1"


def get_parent_process_pid(pid: int) -> int:
    """
    Get the parent process ID of the given process ID.
    """

    if pid == -1:
        # Current Process
        return os.getppid()

    process = psutil.Process(pid)
    return process.ppid()


def get_process_name(pid: int) -> str:
    """
    Get the process name of the given process ID.
    """
    process = psutil.Process(pid)
    return process.name()


def get_process_name_list(pid: List[int]) -> List[str]:
    """
    Get the process name of the given process ID list.
    """
    return [get_process_name(pid) for pid in pid]


def get_chain_of_process(pid: int) -> List[str]:
    """
    Get the chain of process of the given process ID.
    """

    if pid <= 0:
        pid = os.getpid()

    chain = []
    while pid > 0:
        chain.append(pid)
        pid = get_parent_process_pid(pid)
    return chain


def check_is_python_process(pid: int) -> bool:
    try:
        if isinstance(pid, str):
            pid = int(pid)
        process = psutil.Process(pid)
        exe_path = process.exe()
        exe_name = os.path.basename(exe_path)

        index = exe_name.find(".")
        if index > -1:
            exe_name = exe_name[:index]
        exe_name = exe_name.strip().lower()

        return exe_name == "python" or exe_name == "python3"
    except Exception:
        return False


def get_top_python_process_pid(pid: int) -> int:
    """
    Get the top python process ID of the current process.
    """
    pid_list = get_chain_of_process(pid)

    if len(pid_list) < 2:
        return -1

    # Remove Self
    pid_list = pid_list[1:]

    pid_list.reverse()

    for pid in pid_list:
        if check_is_python_process(pid):
            return pid

    return -1


def check_parent_process_name_keywords(keywords: List[str]) -> bool:
    pid_list = get_chain_of_process(get_parent_process_pid(-1))
    p_name_list = get_process_name_list(pid_list)

    for process_name in p_name_list:
        for keyword in keywords:
            if keyword and (keyword in process_name):
                return True

    return False


def is_run_by_gateway() -> bool:
    keywords = ["remote-dev-serv", "launcher.sh"]
    return check_parent_process_name_keywords(keywords)


def is_run_by_vscode_remote() -> bool:
    keywords = ["code-"]
    return check_parent_process_name_keywords(keywords)


def is_run_by_screen() -> bool:
    keywords = ["screen"]
    return check_parent_process_name_keywords(keywords)


def is_run_by_tmux() -> bool:
    keywords = ["tmux"]
    return check_parent_process_name_keywords(keywords)


if __name__ == "__main__":
    print(get_parent_process_pid(-1))
    print(get_process_name(get_parent_process_pid(-1)))

    pid_list = get_chain_of_process(-1)
    print(pid_list)

    p_name_list = get_process_name_list(pid_list)
    print(p_name_list)

    p_is_python_list = [
        check_is_python_process(pid)
        for pid in pid_list
    ]
    print(p_is_python_list)

    print("is_run_by_gateway", is_run_by_gateway())
    print("is_run_by_vscode_remote", is_run_by_vscode_remote())
    print("is_run_by_screen", is_run_by_screen())
    print("is_run_by_tmux", is_run_by_tmux())

    print(get_top_python_process_pid(-1))
