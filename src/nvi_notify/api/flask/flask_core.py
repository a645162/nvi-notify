import html
import json

import flask
import flask_cors
import requests

from nvi_notify.config import settings
from nvi_notify.utils import api_utils

##################################################
# Close Flask Log
if settings.FLASK_LOG_DISABLE:
    import logging

    log = logging.getLogger("werkzeug")
    log.disabled = True
    log.setLevel(logging.ERROR)
##################################################

from nvi_notify.utils import logs

logger = logs.get_logger()
logger.info("Flask server is starting...")
app = flask.Flask(__name__)

if not settings.WEB_SERVER_CORS_ENABLE:
    # 允许所有域进行跨源请求
    flask_cors.CORS(app)
    logger.info("Set CORS for Flask server.")


@app.route("/nvitop_output")
def get_nvitop_output() -> flask.Response:
    command_result = api_utils.get_nvitop_result()
    return flask.Response(
        response=json.dumps({"result": html.escape(command_result)}),
        status=200,
        mimetype="application/json",
    )


@app.route("/machine_user_message", methods=["POST"])
def post_machine_user_message() -> flask.Response:
    final_data: dict = {"haveError": True, "isSucceed": False, "result": "error"}

    if flask.request.method == "POST":
        user_name = flask.request.form["userName"]
        content = flask.request.form["content"]

        api_utils.machine_user_message_backend(
            user_name=user_name,
            content=content,
        )

    return flask.Response(
        response=json.dumps(final_data),
        status=200,
        mimetype="application/json",
    )


@app.route("/system_info")
def get_system_info() -> flask.Response:
    system_info: dict = api_utils.get_system_info_dict()

    return flask.Response(
        response=json.dumps(system_info),
        status=200,
        mimetype="application/json",
    )


@app.route("/gpu_count")
def get_gpu_count() -> flask.Response:
    gpu_count = api_utils.get_gpu_count_backend()

    print("gpu_count =", gpu_count)

    return flask.Response(
        response=json.dumps({"result": gpu_count}),
        status=200,
        mimetype="application/json",
    )


@app.route("/gpu_usage_info")
def get_gpu_usage_info() -> flask.Response:
    gpu_index = flask.request.args.get("gpu_index", default=None, type=int)
    if gpu_index is None:
        gpu_index = flask.request.args.get("gpuIndex", default=None, type=int)

    if gpu_index is None or gpu_index > api_utils.get_gpu_count_backend():
        return flask.Response(
            response=json.dumps({"result": "Invalid GPU Index(gpu_index)."}),
            status=400,
            mimetype="application/json",
        )

    response_gpu_usage = api_utils.get_gpu_usage_dict(gpu_index=gpu_index)

    return flask.Response(
        response=json.dumps(response_gpu_usage),
        status=200,
        mimetype="application/json",
    )


@app.route("/gpu_task_info")
def get_gpu_task_info() -> flask.Response:
    gpu_index = flask.request.args.get("gpu_index", default=None, type=int)
    if gpu_index is None:
        gpu_index = flask.request.args.get("gpuIndex", default=None, type=int)

    if gpu_index is None or gpu_index > api_utils.get_gpu_count_backend():
        return flask.Response(
            response=json.dumps({"result": "Invalid GPU Index(gpu_index)."}),
            status=400,
            mimetype="application/json",
        )

    task_list = api_utils.get_gpu_task_dict_list(gpu_index=gpu_index)

    response_gpu_tasks = {"result": len(task_list), "taskList": task_list}

    return flask.Response(
        response=json.dumps(response_gpu_tasks),
        status=200,
        mimetype="application/json",
    )


@app.route("/disk_usage")
def get_disk_usage() -> flask.Response:
    result = api_utils.get_disk_usage()
    response_disk_usage = {"result": len(result), "diskUsage": result}

    return flask.Response(
        response=json.dumps(response_disk_usage),
        status=200,
        mimetype="application/json",
    )


@app.route("/disk_usage_user")
def get_disk_usage_user() -> flask.Response:
    result = api_utils.get_disk_usage_user_dict_list()
    response_disk_usage = {"result": len(result), "diskUsageUsage": result}

    return flask.Response(
        response=json.dumps(response_disk_usage),
        status=200,
        mimetype="application/json",
    )


@app.route("/")
def get_index():  # noqa: ANN201
    if len(settings.GPU_BOARD_WEB_URL) != 0:
        try:
            response = requests.get(settings.GPU_BOARD_WEB_URL)
            if response.status_code == 200:
                return flask.redirect(settings.GPU_BOARD_WEB_URL)
        except requests.exceptions.RequestException:
            logger.info("GPU board URL cannot be accessed.")
    else:
        logger.info("GPU board URL is not set.")

    command_result = api_utils.get_nvitop_result()
    return flask.render_template(
        "index.html", result=command_result, page_title=settings.SERVER_NAME
    )
