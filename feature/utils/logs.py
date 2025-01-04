# -*- coding: utf-8 -*-

import os
import threading
from typing import Dict

import loguru


class LoggerManager:
    _instance = None
    _lock = threading.Lock()
    _loggers: Dict[str, loguru.Logger] = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_log_dir()
        return cls._instance

    def _init_log_dir(self):
        self.log_dir = "./log"

        if not os.path.exists(self.log_dir):
            os.mkdir(self.log_dir)

        permission_check_file = os.path.join(self.log_dir, "check.log")
        try:
            with open(permission_check_file, "w") as f:
                f.write(str(permission_check_file))
            os.remove(permission_check_file)
        except Exception as e:
            raise RuntimeError(f"无法写入日志目录 {self.log_dir}: {e}")

    def get_logger(self, log_name: str) -> loguru.Logger:
        postfix = ".log"
        with self._lock:
            if log_name not in self._loggers:
                logger = loguru.logger
                log_path = os.path.join(self.log_dir, log_name + postfix)
                logger.add(log_path, retention="30 days", format="{time} | {level} | {message}")
                self._loggers[log_name] = logger
            return self._loggers[log_name]


# Singleton instance
logger_manager = LoggerManager()


def get_logger(log_name: str = "nvinotify") -> loguru.Logger:
    return logger_manager.get_logger(log_name)
