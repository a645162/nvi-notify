# -*- coding: utf-8 -*-

import json
from html import escape

import logging

log = logging.getLogger()
log.setLevel(logging.ERROR)

import requests
from flask import Flask, Response, redirect, render_template, request

from config.settings import (
    GPU_BOARD_WEB_URL,
    SERVER_NAME,
)

from feature.web.web_common import *

from feature.utils.logs import get_logger

# from flask_cors import CORS

logger = get_logger()
logger.info("Flask server is starting...")
app = Flask(__name__)


# 允许所有域进行跨源请求
# CORS(app)
# logger.info("Set CORS for Flask server.")


@app.route("/nvitop_output")
def get_nvitop_output():
    command_result = get_nvitop_result()
    return Response(
        response=json.dumps({"result": escape(command_result)}),
        status=200,
        mimetype="application/json",
    )


@app.route("/machine_user_message", methods=['POST'])
def post_machine_user_message():
    final_data: dict = {
        "haveError": True,
        "isSucceed": False,
        "result": "error"
    }

    if request.method == 'POST':
        user_name = request.form['userName']
        content = request.form['content']

        machine_user_message_backend(
            user_name=user_name,
            content=content,
        )

    return Response(
        response=json.dumps(final_data),
        status=200,
        mimetype="application/json",
    )


@app.route("/system_info")
def get_system_info():
    system_info: dict = get_system_info_dict()

    return Response(
        response=json.dumps(system_info),
        status=200,
        mimetype="application/json",
    )


@app.route("/gpu_count")
def get_gpu_count():
    gpu_count = get_gpu_count_backend()

    print("gpu_count =", gpu_count)

    return Response(
        response=json.dumps({"result": gpu_count}),
        status=200,
        mimetype="application/json",
    )


@app.route("/gpu_usage_info")
def get_gpu_usage_info():
    gpu_index = request.args.get("gpu_index", default=None, type=int)
    if gpu_index is None or gpu_index > get_gpu_count_backend():
        return Response(
            response=json.dumps({"result": "Invalid GPU Index(gpu_index)."}),
            status=400,
            mimetype="application/json",
        )

    response_gpu_usage = get_gpu_usage_dict(gpu_index=gpu_index)

    return Response(
        response=json.dumps(response_gpu_usage),
        status=200,
        mimetype="application/json",
    )


@app.route("/gpu_task_info")
def get_gpu_task_info():
    gpu_index = request.args.get("gpu_index", default=None, type=int)

    if gpu_index is None or gpu_index > get_gpu_count_backend():
        return Response(
            response=json.dumps({"result": "Invalid GPU Index(gpu_index)."}),
            status=400,
            mimetype="application/json",
        )

    task_list = get_gpu_task_dict_list(gpu_index=gpu_index)

    response_gpu_tasks = {"result": len(task_list), "taskList": task_list}

    return Response(
        response=json.dumps(response_gpu_tasks),
        status=200,
        mimetype="application/json",
    )


@app.route("/")
def get_index():
    if len(GPU_BOARD_WEB_URL) != 0:
        try:
            response = requests.get(GPU_BOARD_WEB_URL)
            if response.status_code == 200:
                return redirect(GPU_BOARD_WEB_URL)
        except requests.exceptions.RequestException:
            logger.info("GPU board URL cannot be accessed.")
    else:
        logger.info("GPU board URL is not set.")

    command_result = get_nvitop_result()
    return render_template("index.html", result=command_result, page_title=SERVER_NAME)
