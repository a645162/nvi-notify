import time

from nvi_notify import (
    cpu_monitor,
    gpu_monitor,
    hard_disk_monitor,
    launcher,
    logs,
    settings,
    webhook,
)

logger = logs.get_logger()


def main() -> None:
    logger.info("Main program is starting...")

    # For check env settings
    logger.info(f"Waiting for {settings.WAIT_TIME_BEFORE_START} seconds...")
    logger.info("You can check the environment settings in the meantime.")
    logger.info("Press Ctrl+C to stop the program.")
    time.sleep(settings.WAIT_TIME_BEFORE_START)

    logger.info("Webhook sub program is starting...")
    try:
        webhook.init_webhook()
    except Exception as e:
        logger.error(f"Webhook Init Error: {e}")
        logger.error("Webhook sub program error, please check the configuration.")

    logger.info("CPU Monitor sub program is starting...")
    try:
        cpu_monitor.start_cpu_monitor_all()
    except Exception as e:
        logger.error(f"CPU Monitor Error: {e}")
        logger.error("CPU Monitor sub program error, please check the configuration.")

    logger.info("GPU Monitor sub program is starting...")
    try:
        gpu_monitor.start_gpu_monitor_all()
    except Exception as e:
        logger.error(f"GPU Monitor Error: {e}")
        logger.error("GPU Monitor sub program error, please check the configuration.")

    logger.info("Hard Disk Monitor sub program is starting...")
    try:
        hard_disk_monitor.start_resource_monitor_all()
    except Exception as e:
        logger.error(f"Resource Monitor Error: {e}")
        logger.error(
            "Hard Disk Monitor sub program error, please check the configuration."
        )

    logger.info("API(Web Server) sub program is starting...")
    launcher.start_api_server()


if __name__ == "__main__":
    main()
