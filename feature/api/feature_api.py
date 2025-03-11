from feature.api.flask.flask_starter import start_flask_server_both_background
from feature.utils.logs import get_logger
from config.settings import FLASK_SERVER_PORT

from group_center.tools.dl.ddp_port import check_port

logger = get_logger()


def start_api_server():
    if not check_port(FLASK_SERVER_PORT):
        logger.error("Port is already used!")
        logger.info("Flask Server start is canceled!")
        return

    logger.info("Flask Server is starting...")
    start_flask_server_both_background()
