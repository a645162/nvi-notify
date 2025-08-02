from group_center.tools.dl import ddp_port

from feature.api.flask import flask_starter
from feature.config import settings
from feature.utils import logs

logger = logs.get_logger()


def start_api_server() -> None:
    if not ddp_port.check_port(settings.FLASK_SERVER_PORT):
        logger.error("Port is already used!")
        logger.info("Flask Server start is canceled!")
        return

    logger.info("Flask Server is starting...")
    flask_starter.start_flask_server_both_background()
