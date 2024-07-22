import threading

from config.settings import (
    FLASK_SERVER_HOST,
    FLASK_SERVER_PORT,
)

from feature.web.flask_main import app

from feature.utils.logs import get_logger

logger = get_logger()


def start_flask_server_ipv4():
    logger.info("Starting Flask server(IPV4)...")
    app.run(host=FLASK_SERVER_HOST, port=FLASK_SERVER_PORT, debug=False)


def start_flask_server_both():
    logger.info("Starting Flask server(Both IPV4 and IPV6)...")
    app.run(host="::", port=FLASK_SERVER_PORT, threaded=True)


def start_flask_server_both_background():
    class FlaskThread(threading.Thread):
        def run(self):
            start_flask_server_both()

    FlaskThread().start()


if __name__ == "__main__":
    # app.run(debug=True)
    # start_web_server()
    start_flask_server_both()
