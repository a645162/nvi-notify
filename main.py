# -*- coding: utf-8 -*-

import time

from config.settings import WAIT_TIME_BEFORE_START

from feature.monitor.cpu.monitor import start_cpu_monitor_all
from feature.monitor.gpu.monitor import start_gpu_monitor_all
from feature.monitor.hard_disk.monitor import start_resource_monitor_all

from feature.notify.webhook import init_webhook

from feature.web.flask_starter import start_flask_server_both_background

from feature.utils.logs import get_logger

logger = get_logger()

if __name__ == "__main__":
    logger.info("Main program is starting...")

    # For check env settings
    logger.info(f"Waiting for {WAIT_TIME_BEFORE_START} seconds...")
    logger.info("You can check the environment settings in the meantime.")
    logger.info("Press Ctrl+C to stop the program.")
    time.sleep(WAIT_TIME_BEFORE_START)

    logger.info("Webhook sub program is starting...")
    init_webhook()

    logger.info("CPU Monitor sub program is starting...")
    start_cpu_monitor_all()

    logger.info("GPU Monitor sub program is starting...")
    start_gpu_monitor_all()

    logger.info("Hard Disk Monitor sub program is starting...")
    start_resource_monitor_all()

    logger.info("Web Server sub program is starting...")

    logger.info("Flask Server is starting...")
    start_flask_server_both_background()
