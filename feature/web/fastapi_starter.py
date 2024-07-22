from uvicorn import run


def run_server(log_level="critical"):
    run(
        app="feature.web.fastapi_main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level=log_level,
    )


if __name__ == "__main__":
    run_server(log_level="info")
