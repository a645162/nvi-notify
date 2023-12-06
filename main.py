from monitor import nvitop_monitor
from web import flask_main

if __name__ == '__main__':
    nvitop_monitor.start_monitor_all()
    flask_main.start_web_server()
