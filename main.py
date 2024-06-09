# -*- coding: utf-8 -*-

import time

from config.settings import WAIT_TIME_BEFORE_START
from feature.monitor.CPU.cpu_monitor import start_cpu_monitor_all
from feature.monitor.GPU.nvitop_monitor import start_gpu_monitor_all
from feature.monitor.hardware_resource.resource_monitor import (
    start_resource_monitor_all,
)
from feature.web.flask_main import start_web_server_both
from utils.logs import get_logger

logger = get_logger()

if __name__ == "__main__":
    logger.info("Main program is starting...")

    # For check env settings
    logger.info(f"Waiting for {WAIT_TIME_BEFORE_START} seconds...")
    logger.info("You can check the environment settings in the meantime.")
    logger.info("Press Ctrl+C to stop the program.")
    time.sleep(WAIT_TIME_BEFORE_START)

    logger.info("CPU Monitor sub program is starting...")
    start_cpu_monitor_all()

    logger.info("GPU Monitor sub program is starting...")
    start_gpu_monitor_all()

    logger.info("Hard Disk Monitor sub program is starting...")
    start_resource_monitor_all()

    logger.info("Web server sub program is starting...")
    start_web_server_both()
