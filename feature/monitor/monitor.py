import sys
import threading
import time

from config.settings import GPU_MONITOR_AUTO_RESTART
from feature.utils.logs import get_logger

logger = get_logger()


class Monitor:
    def __init__(self, monitor_name: str):
        self.monitor_name = monitor_name
        self.thread = None
        self.monitor_thread_work = False

    def start_monitor(self, monitor_thread):
        def thread_worker():
            restart_times = 0

            while self.monitor_thread_work:
                if restart_times > 0:
                    logger.debug(
                        f"{self.monitor_name} monitor restart times: {restart_times}"
                    )

                if GPU_MONITOR_AUTO_RESTART and not sys.gettrace():
                    # 需要重启不可以报错导致线程崩溃
                    try:
                        logger.info(f"{self.monitor_name} monitor start")
                        monitor_thread()
                    except Exception as e:
                        logger.error(f"{self.monitor_name} monitor error: {e}")
                        time.sleep(60)
                else:
                    # 不需要重启就正常报错
                    logger.info(f"{self.monitor_name} monitor start")
                    monitor_thread()
                    logger.info(f"{self.monitor_name} monitor stop")
                    break
                restart_times += 1

        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=thread_worker)
        self.monitor_thread_work = True
        self.thread.start()

    def stop_monitor(self):
        self.monitor_thread_work = False
        if self.thread is not None and self.thread.is_alive():
            self.thread.join()
