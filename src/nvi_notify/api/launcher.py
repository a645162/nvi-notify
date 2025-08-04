from nvi_notify.api.flask import flask_launcher
from nvi_notify.config import settings
from nvi_notify.utils import logs, system

logger = logs.get_logger()


def start_api_server() -> None:
    if not system.is_port_in_use(
        settings.FLASK_SERVER_HOST, settings.FLASK_SERVER_PORT
    ):
        logger.error("Port is already used!")
        logger.info("Flask Server start is canceled!")
        return

    logger.info("Flask Server is starting...")
    flask_launcher.start_flask_server_both_background()
