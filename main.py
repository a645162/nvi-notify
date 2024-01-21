import time

from monitor import cpu_monitor, nvitop_monitor
from utils import env
from web import flask_main

if __name__ == "__main__":
    print("GPU MONITOR")
    print("=" * 40)
    # print("GPU_MONITOR_LOCAL_IP")
    # print(env.get_env("GPU_MONITOR_LOCAL_IP"))
    print("GPU_MONITOR_WEBHOOK_WEWORK")
    print(env.get_env("GPU_MONITOR_WEBHOOK_WEWORK"))
    print("GPU_MONITOR_WEBHOOK_WEWORK_WARNING")
    print(env.get_env("GPU_MONITOR_WEBHOOK_WEWORK_WARNING"))
    print("GPU_MONITOR_SLEEP_TIME_START")
    print(env.get_env_time("GPU_MONITOR_SLEEP_TIME_START"))
    print("GPU_MONITOR_SLEEP_TIME_END")
    print(env.get_env_time("GPU_MONITOR_SLEEP_TIME_END"))
    print("DELAY_SEND_SECONDS")
    print(env.get_env("DELAY_SEND_SECONDS"))
    print("=" * 40)
    print("Program will start in 60 seconds...")
    # time.sleep(60)
    print("=" * 40)
    print("Program starting...")

    cpu_monitor.start_cpu_monitor_all()
    nvitop_monitor.start_gpu_monitor_all()
    flask_main.start_web_server()
