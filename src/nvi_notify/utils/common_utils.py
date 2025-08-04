import re
import subprocess
from pathlib import Path


def read_file(path: Path) -> str:
    try:
        with Path.open(path, "r") as f:
            return f.read()
    except (OSError, FileNotFoundError) as e:
        return f"Error reading file: {e}"


def get_terminal_output(
    input_cmd: str, enable_text: bool = True
) -> tuple[int, str, str]:
    """
    执行命令行，返回执行状态和输出信息。

    参数:
    input_cmd (str): 要执行的命令行。

    返回:
    Tuple[int, str, str]: 一个元组，包含执行状态码和输出信息。
    如果执行成功，状态码为0；否则为其他值。
    """
    ret_stdout = ""
    try:
        # 执行命令行，并捕获输出和错误输出
        process = subprocess.run(
            input_cmd, check=False, shell=True, capture_output=True, text=enable_text
        )
        ret_code = process.returncode
        ret_stdout = process.stdout
        ret_stderr = process.stderr
    except subprocess.CalledProcessError as e:
        # 如果发生异常（例如，命令不存在），返回执行状态和异常信息
        ret_code = e.returncode
        ret_stderr = e.output
    except Exception as e:
        ret_code = -1
        ret_stderr = str(e)

    return ret_code, ret_stdout, ret_stderr


def is_safe_in_shell(value: str) -> bool:
    """确保value不包含任何特殊字符或shell元字符

    安全字符：abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-

    参数:
    value (str): 要检查的字符串

    返回:
    bool: 如果字符串只包含安全字符则返回True，否则返回False
    """
    safe_re = re.compile(r"^[a-zA-Z0-9_-]+$")
    return bool(re.match(safe_re, value))


def try_write_file(path: Path) -> None:
    try:
        if not path.exists():
            Path.mkdir(path, mode=0o755, parents=True, exist_ok=True)
        tempfile = path / "tmp_file"
        with Path.open(tempfile, "w") as f:
            f.write(__name__)
        Path.unlink(tempfile)
    except Exception as e:
        raise PermissionError(f"Cannot write to {path}. E: {e}")
