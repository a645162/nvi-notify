import time
from monitor.CPU.cpu_monitor import start_cpu_monitor_all
from monitor.GPU.nvitop_monitor import start_gpu_monitor_all
from web.flask_main import start_web_server_both
from webhook.wework import send_text

if __name__ == "__main__":

    time.sleep(10)  # for check env settings

    start_cpu_monitor_all()
    start_gpu_monitor_all()
    # send_text("str", msg_type="normal")
    start_web_server_both()
