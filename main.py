import time
from monitor.CPU.cpu_monitor import start_cpu_monitor_all
from monitor.GPU.nvitop_monitor import start_gpu_monitor_all
from web.flask_main import start_web_server_both

from utils.logs import get_logger

logger = get_logger()

if __name__ == "__main__":

    logger.info("Main program is starting...")

    time.sleep(10)  # for check env settings

    logger.info("CPU Monitor sub program is starting...")
    start_cpu_monitor_all()

    logger.info("GPU Monitor sub program is starting...")
    start_gpu_monitor_all()

    logger.info("Web server sub program is starting...")
    start_web_server_both()
