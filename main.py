import time

from config.config import local_ip, local_ipv6
from monitor.cpu_monitor import start_cpu_monitor_all
from monitor.nvitop_monitor import start_gpu_monitor_all
from utils.env import get_env_str, get_env_time
from web.flask_main import start_web_server_both
from webhook.wework import send_text_normal

if __name__ == "__main__":
    print("GPU MONITOR")
    print("=" * 40)
    # print("GPU_MONITOR_LOCAL_IP")
    # print(env.get_env("GPU_MONITOR_LOCAL_IP"))
    print("GPU_MONITOR_WEBHOOK_WEWORK")
    print(get_env_str("GPU_MONITOR_WEBHOOK_WEWORK"))
    print("GPU_MONITOR_WEBHOOK_WEWORK_WARNING")
    print(get_env_str("GPU_MONITOR_WEBHOOK_WEWORK_WARNING"))
    print("GPU_MONITOR_SLEEP_TIME_START")
    print(get_env_time("GPU_MONITOR_SLEEP_TIME_START"))
    print("GPU_MONITOR_SLEEP_TIME_END")
    print(get_env_time("GPU_MONITOR_SLEEP_TIME_END"))
    print("DELAY_SEND_SECONDS")
    print(get_env_str("DELAY_SEND_SECONDS"))
    print("=" * 40)
    print("Program will start in 60 seconds...")
    # time.sleep(60)
    print("=" * 40)
    print("Program starting...")

    start_cpu_monitor_all()
    start_gpu_monitor_all()
    # send_text_normal(
    #     f"假期期间，任务提醒功能关闭。\n"
    #     f"可使用WebVPN访问http://{local_ip}查看实时显卡占用情况。"
    #     f"访问http://{local_ip}:8000使用Web版VS Code。"
    # )
    start_web_server_both()
