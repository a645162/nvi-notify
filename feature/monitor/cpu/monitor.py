import time
from typing import Dict

import psutil

from config.settings import TEMPERATURE_MONITOR_SAMPLING_INTERVAL
from feature.monitor.cpu.cpu import CPU
from feature.monitor.memory import Memory
from feature.monitor.monitor import Monitor
from feature.utils.logs import get_logger
from feature.webhook.msg_handler import MessageHandler

logger = get_logger()


class CPUMonitor(Monitor):
    """CPU监控类，负责监控CPU的温度和使用情况"""

    def __init__(self, num_cpu: int) -> None:
        """初始化CPU监控器

        Args:
            num_cpu: CPU数量
        """
        monitor_name = "CPU"
        super().__init__(monitor_name)
        self.num_cpu: int = num_cpu
        self.cpu_dict: Dict[int, CPU] = self.get_cpu_obj()
        logger.info(f"初始化CPU监控器成功，监控CPU数量: {num_cpu}")

    def get_cpu_obj(self) -> Dict[int, CPU]:
        """获取CPU对象字典

        Returns:
            Dict[int, CPU]: CPU索引到CPU对象的映射
        """
        cpu_dict: Dict[int, CPU] = {}
        for idx in range(self.num_cpu):
            cpu_dict[idx] = CPU(idx)
            logger.debug(f"创建CPU {idx} 监控对象")
        return cpu_dict

    def cpu_monitor_thread(self) -> None:
        """CPU监控线程主循环"""
        memory = Memory()
        logger.info("启动CPU监控线程")

        while self.monitor_thread_work:
            try:
                # 更新内存信息
                memory.update()

                # 获取CPU温度信息
                temperature_info = self.get_cpu_temperature()
                if temperature_info[0] == -1.0:
                    MessageHandler.enqueue_except_warning_msg("cpu")
                    logger.warning("获取CPU温度失败，等待10秒后重试")
                    time.sleep(10)
                    continue

                # 更新每个CPU的温度信息
                for cpu in self.cpu_dict.values():
                    cpu.temperature = temperature_info[cpu.idx]
                    if cpu.temperature_samples:  # 确保deque不为空
                        cpu.average_temperature = sum(cpu.temperature_samples) / len(
                            cpu.temperature_samples
                        )

                    # 发送高温警告消息
                    if cpu.high_temperature_trigger:
                        MessageHandler.enqueue_cpu_temperature_warning_msg(
                            cpu.idx, cpu.temperature
                        )
                        logger.warning(f"CPU {cpu.idx} 温度过高: {cpu.temperature}°C")
                    if cpu.high_aver_temperature_trigger:
                        MessageHandler.enqueue_cpu_aver_temperature_warning_msg(
                            cpu.idx, cpu.average_temperature
                        )
                        logger.warning(
                            f"CPU {cpu.idx} 平均温度过高: {cpu.average_temperature}°C"
                        )

                time.sleep(TEMPERATURE_MONITOR_SAMPLING_INTERVAL)

            except Exception as e:
                logger.error(f"CPU监控线程发生异常: {str(e)}")
                time.sleep(5)  # 防止异常导致频繁重启

    @staticmethod
    def get_cpu_temperature() -> Dict[int, float]:
        """获取CPU温度信息

        Returns:
            Dict[int, float]: CPU索引和对应温度的字典，如果获取失败返回{0: -1.0}
        """
        try:
            if not hasattr(psutil, "sensors_temperatures"):
                logger.warning("当前系统不支持获取CPU温度")
                return {0: -1.0}

            temps = psutil.sensors_temperatures()
            if not temps:
                logger.warning("未检测到温度传感器")
                return {0: -1.0}

            cpu_temperature_info: Dict[int, float] = {}
            idx = 0

            # 只处理coretemp和k10temp传感器
            valid_sensors = ("coretemp", "k10temp")
            valid_labels = ("Package", "Tctl")

            for name, entries in temps.items():
                if name not in valid_sensors:
                    continue

                for entry in entries:
                    if any(
                        label in entry.label or label in name for label in valid_labels
                    ):
                        cpu_temperature_info[idx] = entry.current
                        logger.debug(f"检测到CPU {idx} 温度: {entry.current}°C")
                        idx += 1

            return cpu_temperature_info

        except Exception as e:
            logger.error(f"获取CPU温度失败: {str(e)}")
            return {0: -1.0}


def start_cpu_monitor_all() -> None:
    """启动所有CPU监控"""
    NUM_CPU = CPU.get_cpu_num()
    if NUM_CPU is None or NUM_CPU <= 0:
        logger.error("无法获取有效的CPU数量")
        return

    try:
        cpu_monitor = CPUMonitor(NUM_CPU)
        cpu_monitor.start_monitor(cpu_monitor.cpu_monitor_thread)
        logger.info("成功启动所有CPU监控")
    except Exception as e:
        logger.error(f"启动CPU监控失败: {str(e)}")


if __name__ == "__main__":
    start_cpu_monitor_all()
