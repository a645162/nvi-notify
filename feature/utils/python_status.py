import os
import sys

from feature.utils.process.linux_process import (
    is_run_by_gateway,
    is_run_by_screen,
    is_run_by_vscode_remote,
)


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
