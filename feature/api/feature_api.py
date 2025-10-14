import time

from group_center.utils.network.port import check_port, get_pid_by_port
from group_center.utils.process.process import kill_process_list

from config.settings import FLASK_SERVER_PORT
from feature.api.flask.flask_starter import start_flask_server_both_background
from feature.utils.logs import get_logger

logger = get_logger()


def start_api_server():
    if not check_port(FLASK_SERVER_PORT):
        logger.error("Port is already used!")

        pid_list = get_pid_by_port(FLASK_SERVER_PORT)
        if pid_list:
            logger.info(f"Port {FLASK_SERVER_PORT} is used by PIDs: {pid_list}")
            if kill_process_list(pid_list):
                logger.info(f"Killed processes using port {FLASK_SERVER_PORT}.")
            else:
                logger.error(
                    f"Failed to kill processes using port {FLASK_SERVER_PORT}."
                )

            # Wait a moment to ensure the port is released
            time.sleep(2)

            logger.info("Rechecking port status...")
            if not check_port(FLASK_SERVER_PORT):
                logger.error(
                    f"Port {FLASK_SERVER_PORT} is still in use after killing processes."
                )
                logger.info("Flask Server start is canceled!")
                return
        else:
            logger.error(f"Could not find processes using port {FLASK_SERVER_PORT}.")
            logger.info("Flask Server start is canceled!")
            return

    logger.info("Flask Server is starting...")
    start_flask_server_both_background()
