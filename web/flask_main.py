import json
import subprocess
from html import escape

from flask import Flask, Response, render_template

from config.config import server_name, flask_server_host, flask_server_port

app = Flask(__name__)


@app.route("/get_result")
def get_result():
    command_result = run_command("nvitop -U")
    return Response(
        response=json.dumps({"result": escape(command_result)}),
        status=200,
        mimetype="application/json",
    )


@app.route("/")
def index():
    command_result = run_command("nvitop -U")
    return render_template("index.html", result=command_result, page_title=server_name)


def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return str(e), 500


def start_web_server_ipv4():
    app.run(host=flask_server_host, port=flask_server_port, debug=False)


def start_web_server_both():
    app.run(host="::", port=flask_server_port, threaded=True)


if __name__ == "__main__":
    # app.run(debug=True)
    # start_web_server()
    start_web_server_both()
