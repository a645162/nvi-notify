import threading

from src.api.flask import flask_core
from src.config import settings
from src.utils import logs

logger = logs.get_logger()


def start_flask_server_ipv4() -> None:
    logger.info("Starting Flask server(IPV4)...")
    flask_core.app.run(
        host=settings.FLASK_SERVER_HOST, port=settings.FLASK_SERVER_PORT, debug=False
    )


def start_flask_server_both() -> None:
    logger.info("Starting Flask server(Both IPV4 and IPV6)...")
    flask_core.app.run(host="::", port=settings.FLASK_SERVER_PORT, threaded=True)


def start_flask_server_both_background() -> None:
    class FlaskThread(threading.Thread):
        def run(self) -> None:
            start_flask_server_both()

    FlaskThread().start()


if __name__ == "__main__":
    # app.run(debug=True)
    # start_web_server()
    start_flask_server_both()
