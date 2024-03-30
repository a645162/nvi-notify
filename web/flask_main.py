import json
import subprocess
from html import escape
from typing import List

from flask import Flask, Response, render_template, request
from flask_cors import CORS

from config.settings import FLASK_SERVER_HOST, FLASK_SERVER_PORT, SERVER_NAME
from global_variable.global_gpu import (
    global_gpu_info,
    global_gpu_task,
    global_gpu_usage,
)
from monitor.GPU.python_process import PythonGPUProcess

app = Flask(__name__)

# 允许所有域进行跨源请求
CORS(app)


@app.route("/get_result")
def get_result():
    command_result = run_command("nvitop -U")
    return Response(
        response=json.dumps({"result": escape(command_result)}),
        status=200,
        mimetype="application/json",
    )


@app.route("/get_gpu_count")
def get_gpu_count():
    # For debug use
    current_gpu_task = global_gpu_task
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

    current_gpu_processes: List[PythonGPUProcess] = global_gpu_task[gpu_index]

    task_list = []

    for process_obj in current_gpu_processes:
        task_list.append(
            {
                "id": process_obj.pid,
                "name": process_obj.user["name"],
                "debugMode": process_obj.is_debug,
                "projectName": process_obj.project_name,
                "pyFileName": process_obj.python_file,
                "runTime": process_obj.running_time_human,
                "startTimestamp": int(process_obj.start_time) * 1000,
                "gpuMemoryUsage": process_obj.task_gpu_memory >> 10 >> 10,
                "worldSize": process_obj.world_size,
                "localRank": process_obj.local_rank,
                "condaEnv": process_obj.conda_env,
                "command": process_obj.command,
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
    command_result = run_command("nvitop -U")
    return render_template("index.html", result=command_result, page_title=SERVER_NAME)


def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return str(e), 500


def start_web_server_ipv4():
    app.run(host=FLASK_SERVER_HOST, port=FLASK_SERVER_PORT, debug=False)


def start_web_server_both():
    app.run(host="::", port=FLASK_SERVER_PORT, threaded=True)


if __name__ == "__main__":
    # app.run(debug=True)
    # start_web_server()
    start_web_server_both()
