from feature.api.flask.flask_starter import start_flask_server_both_background
from feature.utils.logs import get_logger

logger = get_logger()


def start_api_server():
    logger.info("Flask Server is starting...")
    start_flask_server_both_background()
