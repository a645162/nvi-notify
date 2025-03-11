import subprocess
from typing import Tuple


def cat_info(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except (IOError, FileNotFoundError) as e:
        return f"Error reading file: {e}"


def do_command(cmd: str, text: bool = True) -> Tuple[int, str, str]:
    """
    执行命令行，返回执行状态和输出信息。

    参数:
    cmd (str): 要执行的命令行。

    返回:
    Tuple[int, str, str]: 一个元组，包含执行状态码和输出信息。
    如果执行成功，状态码为0；否则为其他值。
    """
    output_stdout = ""
    try:
        # 执行命令行，并捕获输出和错误输出
        process = subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text
        )
        output_stdout = process.stdout
        output_stderr = process.stderr
        return_code = process.returncode
    except subprocess.CalledProcessError as e:
        # 如果发生异常（例如，命令不存在），返回执行状态和异常信息
        return_code = e.returncode
        output_stderr = e.output
    except Exception as e:
        return_code = -1
        output_stderr = str(e)

    return return_code, output_stdout, output_stderr


def is_safe_in_shell(value):
    # 简单示例：确保value不包含任何特殊字符或shell元字符
    safe_characters = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    )
    return all(char in safe_characters for char in value)
