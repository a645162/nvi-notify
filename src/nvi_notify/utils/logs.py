from pathlib import Path

from loguru import (
    Logger as luguru_Logger,
    logger as loguru_logger,
)

from nvi_notify.utils import common_utils


class Logger:
    def __init__(self) -> None:
        log_dir = Path("./log")

        common_utils.try_write_file(log_dir)
        log_path = Path(log_dir / "nvinotify.log")
        self.instance = loguru_logger
        self.instance.add(log_path, retention="30 days")


def get_logger() -> luguru_Logger:
    return logger.instance


logger = Logger()
