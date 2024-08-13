import os
import psutil
from typing import List


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


def get_top_python_process_pid(pid: int) -> int:
    """
    Get the top python process ID of the current process.
    """
    pid_list = get_chain_of_process(pid)

    if len(pid_list) < 2:
        return -1

    pid_list = pid_list[1:]
    pid_list.reverse()

    for pid in pid_list:
        if get_process_name(pid) == "python":
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

    print("is_run_by_gateway", is_run_by_gateway())
    print("is_run_by_vscode_remote", is_run_by_vscode_remote())
    print("is_run_by_screen", is_run_by_screen())
    print("is_run_by_tmux", is_run_by_tmux())

    print(get_top_python_process_pid(-1))
