# -*- coding: utf-8 -*-
import os

import loguru

from feature.utils.common_utils import check_permission


class Logger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance

    def _initialize_logger(self):
        log_dir = "./log"

        check_permission(log_dir)
        log_path = os.path.join(log_dir, "nvinotify.log")
        self.logger = loguru.logger
        self.logger.add(log_path, retention="30 days")

    def get_logger(self):
        return self.logger

def get_logger() -> loguru.logger:
    return Logger().get_logger()
