# -*- coding: utf-8 -*-

import json
import subprocess
from html import escape
from typing import List

import requests
from flask import Flask, Response, redirect, render_template, request
# from flask_cors import CORS


from config.settings import (
    FLASK_SERVER_HOST,
    FLASK_SERVER_PORT,
    GPU_BOARD_WEB_URL,
    SERVER_NAME,
)
from feature.monitor.gpu.gpu_process import GPUProcessInfo
from global_variable.global_gpu import (
    global_gpu_info,
    global_gpu_task,
    global_gpu_usage,
)
from global_variable.global_system import global_system_info
from utils.logs import get_logger

logger = get_logger()


logger.info("Flask server is starting...")
app = Flask(__name__)

# 允许所有域进行跨源请求
# CORS(app)
# logger.info("Set CORS for Flask server.")


@app.route("/get_result")
def get_result():
    command_result = run_command("nvitop -U")
    return Response(
        response=json.dumps({"result": escape(command_result)}),
        status=200,
        mimetype="application/json",
    )


@app.route("/get_system_info")
def get_system_info():
    system_info: dict = {
        "memoryPhysicTotalMb": 4096,
        "memoryPhysicUsedMb": 2048,
        "memorySwapTotalMb": 4096,
        "memorySwapUsedMb": 2048,
    }

    system_info.update(global_system_info)

    return Response(
        response=json.dumps(system_info),
        status=200,
        mimetype="application/json",
    )


@app.route("/get_gpu_count")
def get_gpu_count():
    # For debug use
    # current_gpu_task = global_gpu_task
    return Response(
        response=json.dumps({"result": len(global_gpu_task)}),
        status=200,
        mimetype="application/json",
    )


@app.route("/get_gpu_usage")
def get_gpu_usage():
    gpu_index = request.args.get("gpu_index", default=None, type=int)
    if gpu_index is None or gpu_index > len(global_gpu_usage):
        return Response(
            response=json.dumps({"result": "Invalid GPU Index(gpu_index)."}),
            status=400,
            mimetype="application/json",
        )

    current_gpu_info = global_gpu_info[gpu_index]
    current_gpu_usage = global_gpu_usage[gpu_index]

    response_gpu_usage = {
        "result": len(global_gpu_usage),
        "gpuName": "Test GPU",
        "coreUsage": "0",
        "memoryUsage": "0",
        "gpuMemoryUsage": "0GiB",
        "gpuMemoryTotal": "0GiB",
        "gpuPowerUsage": "0",
        "gpuTDP": "0",
        "gpuTemperature": "0",
    }

    response_gpu_usage.update(current_gpu_info)
    response_gpu_usage.update(current_gpu_usage)

    return Response(
        response=json.dumps(response_gpu_usage),
        status=200,
        mimetype="application/json",
    )


@app.route("/get_gpu_task")
def get_gpu_task():
    gpu_index = request.args.get("gpu_index", default=None, type=int)

    if gpu_index is None or gpu_index > len(global_gpu_task):
        return Response(
            response=json.dumps({"result": "Invalid GPU Index(gpu_index)."}),
            status=400,
            mimetype="application/json",
        )

    current_gpu_processes: List[GPUProcessInfo] = global_gpu_task[gpu_index]

    task_list = []

    for process_obj in current_gpu_processes:
        task_list.append(
            {
                "id": process_obj.pid,
                "name": process_obj.user.name_cn,
                "debugMode": process_obj.is_debug,
                "projectName": process_obj.project_name,
                "pyFileName": process_obj.python_file,
                "runTime": process_obj.running_time_human,
                "startTimestamp": int(process_obj.start_time) * 1000,
                "gpuMemoryUsage": int(process_obj.task_gpu_memory >> 10 >> 10),
                "gpuMemoryUsageMax": int(process_obj.task_gpu_memory_max >> 10 >> 10),
                "worldSize": process_obj.world_size,
                "localRank": process_obj.local_rank,
                "condaEnv": process_obj.conda_env,
                "screenSessionName": process_obj.screen_session_name,
                "pythonVersion": process_obj.python_version,
                "command": process_obj.command,
                "taskMainMemoryMB": int(process_obj.task_main_memory_mb),
                "cudaRoot": str(process_obj.cuda_root),
                "cudaVersion": str(process_obj.cuda_version),
            }
        )

    response_gpu_tasks = {"result": len(task_list), "taskList": task_list}

    return Response(
        response=json.dumps(response_gpu_tasks),
        status=200,
        mimetype="application/json",
    )


@app.route("/")
def index():
    if len(GPU_BOARD_WEB_URL) != 0:
        try:
            response = requests.get(GPU_BOARD_WEB_URL)
            if response.status_code == 200:
                return redirect(GPU_BOARD_WEB_URL)
        except requests.exceptions.RequestException:
            pass
    else:
        logger.info("GPU board URL is not set or cannot be accessed.")

    command_result = run_command("nvitop -U")
    return render_template("index.html", result=command_result, page_title=SERVER_NAME)


def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return str(e), 500


def start_web_server_ipv4():
    logger.info("Starting Flask server(IPV4)...")
    app.run(host=FLASK_SERVER_HOST, port=FLASK_SERVER_PORT, debug=False)


def start_web_server_both():
    logger.info("Starting Flask server(Both IPV4 and IPV6)...")
    app.run(host="::", port=FLASK_SERVER_PORT, threaded=True)


if __name__ == "__main__":
    # app.run(debug=True)
    # start_web_server()
    start_web_server_both()
