# -*- coding: utf-8 -*-

import os
import loguru

log_dir = "./log"

# Check Log Directory
if not os.path.exists(log_dir):
    os.mkdir(log_dir)

# Permission Check
try:
    test_file = os.path.join(log_dir, "test.log")
    with open(test_file, "w") as f:
        f.write(str(test_file))
    os.remove(test_file)
except Exception as e:
    print("Cannot write to log directory.")
    print(e)
    exit(1)

log_path = os.path.join(log_dir, "nvinotify.log")

logger = loguru.logger

logger.add(log_path, retention="30 days")


def get_logger() -> loguru.logger:
    return logger
