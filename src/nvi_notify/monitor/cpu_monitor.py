import time

import psutil

from nvi_notify.base import monitor
from nvi_notify.config import settings
from nvi_notify.entity import cpu, memory
from nvi_notify.utils import logs
from nvi_notify.webhook import message_handler

logger = logs.get_logger()


class CPUMonitor(monitor.MonitorBase):
    def __init__(self, num_cpu: int) -> None:
        monitor_name = "CPU"
        super().__init__(monitor_name)
        self.num_cpu: int = num_cpu
        self.cpu_dict: dict[int, cpu.CPU] = self.get_cpu_obj()

    def get_cpu_obj(self) -> dict[int, cpu.CPU]:
        cpu_dict: dict[int, cpu.CPU] = {}
        for idx in range(self.num_cpu):
            cpu_dict[idx] = cpu.CPU(idx)

        return cpu_dict

    def cpu_monitor_thread(self) -> None:
        memory_info = memory.Memory()
        while self.monitor_thread_work:
            memory_info.update()

            temperature_info = self.get_cpu_temperature()
            # 检查是否有有效的温度数据
            if not temperature_info or -1.0 in temperature_info.values():
                message_handler.enqueue_except_warning_msg("cpu")
                time.sleep(10)
                continue

            for _cpu in self.cpu_dict.values():
                if _cpu.idx not in temperature_info:
                    logger.warning(f"No temperature data available for CPU {_cpu.idx}")
                    continue

                _cpu.temperature = temperature_info[_cpu.idx]
                _cpu.average_temperature = sum(_cpu.temperature_samples) / len(
                    _cpu.temperature_samples
                )
                if _cpu.high_temperature_trigger:
                    message_handler.enqueue_cpu_temperature_warning_msg(
                        _cpu.idx, _cpu.temperature
                    )
                if _cpu.high_aver_temperature_trigger:
                    message_handler.enqueue_cpu_aver_temperature_warning_msg(
                        _cpu.idx, _cpu.average_temperature
                    )

            time.sleep(settings.TEMPERATURE_MONITOR_SAMPLING_INTERVAL)

    @staticmethod
    def get_cpu_temperature() -> dict[int, float]:
        if not hasattr(psutil, "sensors_temperatures"):
            logger.warning(
                "psutil.sensors_temperatures() is not available on this platform."
            )
            return {0: -1.0}

        try:
            temps = psutil.sensors_temperatures()  # type: ignore
        except NotImplementedError:
            logger.warning("Temperature sensors are not supported on this system.")
            return {0: -1.0}

        cpu_temperature_info: dict[int, float] = {}
        idx = 0
        for name, entries in temps.items():
            if name not in ("coretemp", "k10temp"):
                continue
            for entry in entries:
                if not (
                    ("Package" in entry.label or "Package" in name)
                    or ("Tctl" in entry.label)
                ):
                    continue
                cpu_temperature_info.update({idx: entry.current})
                idx += 1

        return cpu_temperature_info


def start_cpu_monitor_all() -> None:
    NUM_CPU = cpu.CPU.get_cpu_num()  # noqa: N806
    if NUM_CPU is None:
        logger.error("Cannot get the number of CPU.")
        return

    cpu_monitor = CPUMonitor(NUM_CPU)
    cpu_monitor.start_monitor(cpu_monitor.cpu_monitor_thread)


if __name__ == "__main__":
    start_cpu_monitor_all()
