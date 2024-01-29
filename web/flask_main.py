import json
import subprocess
from html import escape

from flask import Flask, Response, render_template

from config.config import server_name, web_server_host, web_server_port

app = Flask(__name__)


@app.route("/get_result")
def get_result():
    command_result = run_command("nvitop -1")
    return Response(
        response=json.dumps({"result": escape(command_result)}),
        status=200,
        mimetype="application/json",
    )


@app.route("/")
def index():
    command_result = run_command("nvitop -1")
    return render_template("index.html", result=command_result, page_title=server_name)


def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return str(e), 500


def start_web_server_ipv4():
    app.run(host=web_server_host, port=web_server_port, debug=False)


def start_web_server_both():
    app.run(host="::", port=web_server_port, threaded=True)


if __name__ == "__main__":
    # app.run(debug=True)
    # start_web_server()
    start_web_server_both()
