import time

from feature.api.feature_api import start_api_server
from feature.config.settings import WAIT_TIME_BEFORE_START
from feature.monitor.cpu.monitor import start_cpu_monitor_all
from feature.monitor.gpu.monitor import start_gpu_monitor_all
from feature.monitor.hard_disk.monitor import start_resource_monitor_all
from feature.utils import logs
from feature.webhook.webhook import init_webhook

logger = logs.get_logger()

if __name__ == "__main__":
    logger.info("Main program is starting...")

    # For check env settings
    logger.info(f"Waiting for {WAIT_TIME_BEFORE_START} seconds...")
    logger.info("You can check the environment settings in the meantime.")
    logger.info("Press Ctrl+C to stop the program.")
    time.sleep(WAIT_TIME_BEFORE_START)

    logger.info("Webhook sub program is starting...")
    try:
        init_webhook()
    except Exception as e:
        logger.error(f"Webhook Init Error: {e}")
        logger.error("Webhook sub program error, please check the configuration.")

    logger.info("CPU Monitor sub program is starting...")
    try:
        start_cpu_monitor_all()
    except Exception as e:
        logger.error(f"CPU Monitor Error: {e}")
        logger.error("CPU Monitor sub program error, please check the configuration.")

    logger.info("GPU Monitor sub program is starting...")
    try:
        start_gpu_monitor_all()
    except Exception as e:
        logger.error(f"GPU Monitor Error: {e}")
        logger.error("GPU Monitor sub program error, please check the configuration.")

    logger.info("Hard Disk Monitor sub program is starting...")
    try:
        start_resource_monitor_all()
    except Exception as e:
        logger.error(f"Resource Monitor Error: {e}")
        logger.error(
            "Hard Disk Monitor sub program error, please check the configuration."
        )

    logger.info("API(Web Server) sub program is starting...")
    start_api_server()
