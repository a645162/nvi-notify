import hashlib
import subprocess
from typing import Tuple


def get_md5_hash(input: str) -> str:
    md5_hash = hashlib.md5(input.encode('utf-8'))
    return md5_hash.hexdigest()

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
        # 处理其他可能发生的异常
        return_code = 1
        output_stderr = str(e)

    return return_code, output_stdout, output_stderr
