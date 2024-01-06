from monitor import nvitop_monitor
from web import flask_main
from utils import env

import time

if __name__ == '__main__':
    print("GPU MONITOR")
    print("=" * 40)
    print("GPU_MONITOR_WEBHOOK_WEWORK")
    print(env.get_env("GPU_MONITOR_WEBHOOK_WEWORK"))
    print("GPU_MONITOR_SLEEP_TIME_START")
    print(env.get_env_time("GPU_MONITOR_SLEEP_TIME_START"))
    print("GPU_MONITOR_SLEEP_TIME_END")
    print(env.get_env_time("GPU_MONITOR_SLEEP_TIME_END"))
    print("=" * 40)
    print("Program will start in 60 seconds...")
    time.sleep(60)
    print("=" * 40)
    print("Program starting...")

    nvitop_monitor.start_monitor_all()
    flask_main.start_web_server()
