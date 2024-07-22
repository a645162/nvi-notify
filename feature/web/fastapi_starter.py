import threading

from uvicorn import run

from config.settings import (
    WEB_SERVER_HOST,
    FASTAPI_SERVER_PORT,
)

from feature.utils.logs import get_logger

logger = get_logger()


def run_server(log_level="critical"):
    run(
        app="feature.web.fastapi_main:app",
        host="0.0.0.0",
        port=8081,
        reload=True,
        log_level=log_level,
    )


def start_fastapi_server_ipv4(log_level="critical"):
    logger.info("Starting Fastapi server(IPV4)...")
    run(
        app="feature.web.fastapi_main:app",
        host=WEB_SERVER_HOST,
        port=FASTAPI_SERVER_PORT,
        reload=True,
        log_level=log_level,
    )


def start_fastapi_server_ipv4_background(log_level="critical"):
    class FastapiThread(threading.Thread):
        def run(self):
            start_fastapi_server_ipv4(log_level=log_level)

    FastapiThread().start()


if __name__ == "__main__":
    run_server(log_level="info")
