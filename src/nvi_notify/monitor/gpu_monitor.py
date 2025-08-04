import sys
import threading
import time
import traceback
from collections.abc import Callable

import pynvml
from group_center.core import path as gc_core_path
from group_center.core.feature import custom_client_message

from nvi_notify.api import data_manager
from nvi_notify.base import monitor
from nvi_notify.config import settings
from nvi_notify.database import sqlite
from nvi_notify.entity import gpu, process
from nvi_notify.monitor import enums as monitor_enums
from nvi_notify.utils import logs, process_utils
from nvi_notify.webhook import (
    center_message,
    enums as webhook_enums,
    message_handler,
    webhook,
)

logger = logs.get_logger()
sql = sqlite.get_sql()
data_manager_ins = data_manager.get_data_manager()


class NvidiaMonitor(monitor.MonitorBase):
    def __init__(self, num_gpu: int) -> None:
        super().__init__("GPU")
        self.num_gpu = num_gpu
        self.is_multi_gpu_machine: bool = num_gpu > 1
        self.monitor_launch_flag = True
        self.total_num_task = 0

        self.gpu_obj_dict: dict[int, gpu.GPU] = self.get_gpu_obj()

        self.all_processes: dict[int, process.GPUProcessInfo] = {}

        # GPU占用率监控历史记录
        self.process_gpu_usage_history: dict[int, process.GPUProcessInfo] = {}

    def get_gpu_obj(self) -> dict[int, gpu.GPU]:
        gpu_dict = {}
        for idx in range(settings.NUM_GPU):
            gpu_dict[idx] = gpu.GPU(idx, self.is_multi_gpu_machine)

        return gpu_dict

    def gpu_monitor_thread(self) -> None:
        while self.monitor_thread_work:
            self.total_num_task = 0
            current_all_processes = {}

            for idx, _gpu in self.gpu_obj_dict.items():
                _gpu.update()
                self.total_num_task += _gpu.num_task
                current_all_processes.update(_gpu.processes)

                # 监控GPU占用率 - 使用增量更新逻辑
                self.monitor_gpu_usage_for_processes(_gpu.processes)

                # Get gpu status info for webhook msg
                if sys.gettrace() or not self.monitor_launch_flag:
                    continue

                # Send to Group Center
                center_message.gpu_monitor_start(idx)
                sql.check_finish_task(_gpu.processes, idx)

            # 更新全局进程字典，但不清空历史记录
            self.all_processes = current_all_processes

            if self.should_send_monitor_launch_msg:
                self.send_gpu_monitor_launch_msg()

            # Cleanup
            gc_core_path.cleanup_unused_rt_files()

            time.sleep(settings.GPU_MONITOR_SAMPLING_INTERVAL)

    def monitor_gpu_usage_for_processes(
        self, current_processes: dict[int, process.GPUProcessInfo]
    ) -> None:
        """监控进程的GPU和CPU占用率，检测连续零占用率"""
        for pid, process_info in current_processes.items():
            # 如果历史记录中存在该进程，使用历史对象并更新其动态信息
            if pid in self.process_gpu_usage_history:
                # 使用历史对象，保持连续性
                historical_process = self.process_gpu_usage_history[pid]
                # 更新动态信息
                historical_process.update()
                # 使用历史对象进行后续处理
                process_to_check = historical_process
            else:
                # 新进程，使用当前对象
                process_to_check = process_info
                # 将新进程加入历史记录
                self.process_gpu_usage_history[pid] = process_info

            # 检查是否需要发送零占用率报警
            alert_info = process_to_check.should_send_idle_alert()

            # 只有当CPU和GPU都需要报警时才发送（如果相应开关都启用）
            should_send_combined_alert = self._should_send_combined_alert(alert_info)

            if should_send_combined_alert:
                self.send_combined_zero_usage_alert(process_to_check, alert_info)

        # 清理已结束进程的历史记录
        self.cleanup_finished_processes(current_processes)

    def cleanup_finished_processes(
        self, current_processes: dict[int, process.GPUProcessInfo]
    ) -> None:
        """清理已结束进程的GPU占用率历史记录"""

        finished_pids = []
        for pid in self.process_gpu_usage_history.keys():
            if pid not in current_processes or not process_utils.check_process_exists(
                pid
            ):
                finished_pids.append(pid)

        for pid in finished_pids:
            del self.process_gpu_usage_history[pid]

    @staticmethod
    def calculate_zero_time_str(count: int) -> str:
        """根据计数计算总共为0的时间"""
        total_seconds = settings.GPU_MONITOR_SAMPLING_INTERVAL * count

        if total_seconds < 60:
            return f"{total_seconds}秒"

        minutes = total_seconds // 60
        if minutes < 60:
            remaining_seconds = total_seconds % 60
            if remaining_seconds > 0:
                return f"{minutes}分钟{remaining_seconds}秒"
            else:
                return f"{minutes}分钟"

        hours = minutes // 60
        if hours < 24:
            remaining_minutes = minutes % 60
            if remaining_minutes > 0:
                return f"{hours}小时{remaining_minutes}分钟"
            else:
                return f"{hours}小时"

        days = hours // 24
        remaining_hours = hours % 24
        if remaining_hours > 0:
            return f"{days}天{remaining_hours}小时"
        else:
            return f"{days}天"

    @staticmethod
    def get_detection_interval_str() -> str:
        """获取检测间隔时间字符串"""
        total_seconds = (
            settings.GPU_MONITOR_SAMPLING_INTERVAL * settings.MAX_CONSECUTIVE_ZERO_COUNT
        )

        if total_seconds < 60:
            return f"{total_seconds}秒"

        minutes = total_seconds // 60
        if minutes < 60:
            remaining_seconds = total_seconds % 60
            if remaining_seconds > 0:
                return f"{minutes}分钟{remaining_seconds}秒"
            else:
                return f"{minutes}分钟"

        hours = minutes // 60
        if hours < 24:
            remaining_minutes = minutes % 60
            if remaining_minutes > 0:
                return f"{hours}小时{remaining_minutes}分钟"
            else:
                return f"{hours}小时"

        days = hours // 24
        remaining_hours = hours % 24
        if remaining_hours > 0:
            return f"{days}天{remaining_hours}小时"
        else:
            return f"{days}天"

    @staticmethod
    def gpu_zero_time_str() -> str:
        """获取零占用率检测间隔时间字符串"""
        return NvidiaMonitor.get_detection_interval_str()

    def _should_send_combined_alert(self, alert_info: dict) -> bool:
        """
        判断是否应该发送综合报警
        只有当启用的监控项都满足报警条件时才返回True
        """
        # 获取各项是否需要报警
        gpu_alert_needed = alert_info["should_send_gpu_idle_msg"]
        cpu_alert_needed = alert_info["should_send_cpu_idle_msg"]

        # 检查启用的监控项
        gpu_enabled = settings.GPU_CONSECUTIVE_ZERO_ENABLE
        cpu_enabled = settings.CPU_CONSECUTIVE_ZERO_ENABLE

        # 如果两个监控都启用，则需要都满足条件才发送
        if gpu_enabled and cpu_enabled:
            return gpu_alert_needed and cpu_alert_needed

        # 如果只启用GPU监控
        elif gpu_enabled and not cpu_enabled:
            return gpu_alert_needed

        # 如果只启用CPU监控
        elif cpu_enabled and not gpu_enabled:
            return cpu_alert_needed

        # 如果都没启用，不发送报警
        else:
            return False

    def send_combined_zero_usage_alert(
        self, process_info: "process.GPUProcessInfo", alert_info: dict
    ) -> None:
        """发送综合的零占用率报警"""
        try:
            # 检查dummy逻辑
            if not self._should_send_combined_alert_dummy_check(process_info):
                logger.info(
                    f"Combined alert blocked by dummy check for process {process_info.pid}"
                )
                return

            # 构建报警消息
            alert_msg_parts = [
                f"🚨 [GPU {process_info.gpu_id}] 资源 0% 占用率报警 🚨\n"
            ]

            # 基本信息
            alert_msg_parts.extend(
                [
                    f"进程PID: {process_info.pid}\n",
                    f"进程名称: {process_info.project_name}-{process_info.python_file}\n",
                    f"用户: {process_info.user.name_cn if process_info.user else '未知'}\n",
                    "\n",
                    f"检测间隔: {self.get_detection_interval_str()}\n",
                    "\n",
                ]
            )

            # 添加具体的占用率信息和统计信息
            if (
                settings.GPU_CONSECUTIVE_ZERO_ENABLE
                and alert_info["should_send_gpu_idle_msg"]
            ):
                # 使用报警次数乘以检测间隔计算总时间
                gpu_total_zero_time = self.calculate_zero_time_str(
                    process_info.total_gpu_idle_alert_count
                    * process_info.max_idle_count
                )
                alert_msg_parts.append(
                    f"当前进程GPU占用率: {process_info.gpu_utilization:.1f}%\n"
                )
                alert_msg_parts.append(
                    f"GPU零占用计次: {process_info.total_gpu_idle_alert_count}\n"
                )
                alert_msg_parts.append(f"GPU总共0%时间: {gpu_total_zero_time}\n")

            if (
                settings.CPU_CONSECUTIVE_ZERO_ENABLE
                and alert_info["should_send_cpu_idle_msg"]
            ):
                # 使用报警次数乘以检测间隔计算总时间
                cpu_total_zero_time = self.calculate_zero_time_str(
                    process_info.total_cpu_idle_alert_count
                    * process_info.max_idle_count
                )
                alert_msg_parts.append(
                    f"当前进程CPU占用率: {process_info.cpu_percent:.1f}%\n"
                )
                alert_msg_parts.append(
                    f"CPU零占用计次: {process_info.total_cpu_idle_alert_count}\n"
                )
                alert_msg_parts.append(f"CPU总共0%时间: {cpu_total_zero_time}\n")

            alert_msg_parts.extend(
                [
                    f"\n已经运行: {process_info.running_time_human}\n\n",
                    f"报警时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n",
                ]
            )

            alert_msg = "".join(alert_msg_parts)
            msg = message_handler.wrap_normal_level_msg(alert_msg)

            # 发送到 webhook
            webhook.Webhook.enqueue_msg_to_webhook(
                msg,
                monitor_enums.MsgType.NORMAL,
                enable_name=webhook_enums.AllWebhookName.ALL,
            )

            # 通过 group_center 发送到群组
            custom_client_message.machine_message_directly(
                server_name=settings.SERVER_NAME,
                server_name_eng=settings.SERVER_NAME_SHORT,
                content=msg,
                at=process_info.user.name_cn if process_info.user else "",
            )

            # 通过 group_center 发送给用户
            if process_info.user and process_info.user.name_cn:
                custom_client_message.machine_user_message_directly(
                    user_name=process_info.user.name_cn, content=msg
                )

            logger.warning(
                f"Combined zero usage alert sent for process {process_info.pid} (GPU count: {process_info.total_gpu_idle_alert_count}, CPU count: {process_info.total_cpu_idle_alert_count})"
            )

            # 发送成功后，重置当前报警标志，准备下一轮检测
            if (
                settings.GPU_CONSECUTIVE_ZERO_ENABLE
                and alert_info["should_send_gpu_idle_msg"]
            ):
                process_info.should_send_gpu_idle_msg = False

            if (
                settings.CPU_CONSECUTIVE_ZERO_ENABLE
                and alert_info["should_send_cpu_idle_msg"]
            ):
                process_info.should_send_cpu_idle_msg = False

        except Exception as e:
            logger.error(f"Failed to send combined zero usage alert: {e}")

    def _should_send_combined_alert_dummy_check(
        self, process_info: process.GPUProcessInfo
    ) -> bool:
        """
        综合报警发送前的dummy检测逻辑
        """
        if (
            process_info.is_debug
            or process_info.running_time_in_seconds < 300
            or process_info.ignore_task
        ):
            return False

        return True

    def send_zero_cpu_usage_alert(self, process_info: "process.GPUProcessInfo") -> None:
        """发送CPU零占用率报警（已废弃，请使用综合报警）"""
        logger.warning(
            "send_zero_cpu_usage_alert is deprecated, use send_combined_zero_usage_alert instead"
        )

    def send_zero_gpu_usage_alert(self, process_info: "process.GPUProcessInfo") -> None:
        """发送GPU零占用率报警（已废弃，请使用综合报警）"""
        logger.warning(
            "send_zero_gpu_usage_alert is deprecated, use send_combined_zero_usage_alert instead"
        )

    def _should_send_gpu_idle_msg_dummy_check(
        self, process_info: "process.GPUProcessInfo"
    ) -> bool:
        """
        GPU报警发送前的dummy检测逻辑（已废弃）
        """
        return self._should_send_combined_alert_dummy_check(process_info)

    def _should_send_cpu_idle_msg_dummy_check(
        self, process_info: "process.GPUProcessInfo"
    ) -> bool:
        """
        CPU报警发送前的dummy检测逻辑（已废弃）
        """
        return self._should_send_combined_alert_dummy_check(process_info)

    @property
    def should_send_monitor_launch_msg(self) -> bool:
        if not self.monitor_launch_flag:
            return False
        else:
            self.monitor_launch_flag = False
        return settings.WEBHOOK_SEND_LAUNCH_MESSAGE and self.total_num_task > 0

    def send_gpu_monitor_launch_msg(self) -> None:
        launch_msg_text = []

        for _gpu in self.gpu_obj_dict.values():
            _gpu.get_all_tasks_msg_body()
            launch_msg_text.append(
                "\n"
                + _gpu.gpu_tasks_num_msg_header
                + _gpu.all_tasks_msg_body
                + _gpu.gpu_status_msg
            )

        if len(launch_msg_text) > 0:
            msg = message_handler.wrap_normal_level_msg(
                "GPU监控启动" + "".join(launch_msg_text)
            )
            webhook.Webhook.enqueue_msg_to_webhook(
                msg,
                monitor_enums.MsgType.NORMAL,
                enable_name=webhook_enums.AllWebhookName.ALL,
            )

    def start_monitor(self, monitor_thread: Callable) -> None:
        def thread_worker() -> None:
            restart_times = 0

            while self.monitor_thread_work:
                if restart_times > 0:
                    logger.debug(
                        f"{self.monitor_name} monitor restart times: {restart_times}"
                    )

                if settings.GPU_MONITOR_AUTO_RESTART and not sys.gettrace():
                    # 需要重启不可以报错导致线程崩溃
                    try:
                        logger.info(f"{self.monitor_name} monitor start")
                        monitor_thread()
                    except pynvml.NVMLError as e:
                        msg = f"{self.monitor_name} monitor error: {e}\n{traceback.format_exc()}"
                        logger.error(msg)
                        self.send_gpu_error_msg(msg)
                        time.sleep(600)
                    except Exception as e:
                        logger.error(
                            f"{self.monitor_name} monitor error: {e}\n{traceback.format_exc()}"
                        )
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

    def send_gpu_error_msg(self, error_msg: str) -> None:
        msg = message_handler.wrap_normal_level_msg(error_msg)
        webhook.Webhook.enqueue_msg_to_webhook(
            msg,
            monitor_enums.MsgType.WARNING,
            enable_name=webhook_enums.AllWebhookName.ALL,
        )


def init_global_gpu_var() -> None:
    default_gpu_info_dict = {
        "gpuName": "NVIDIA GeForce RTX",
        "gpuTDP": "0W",
    }
    default_gpu_usage_dict = {
        "coreUsage": "0",
        "memoryUsage": "0",
        "gpuMemoryUsage": "0GiB",
        "gpuMemoryTotal": "0GiB",
        "gpuPowerUsage": "0",
        "gpuTemperature": "0",
    }

    data_manager_ins.gpu_info.extend(
        default_gpu_info_dict.copy() for _ in range(settings.NUM_GPU)
    )
    data_manager_ins.gpu_usage.extend(
        default_gpu_usage_dict.copy() for _ in range(settings.NUM_GPU)
    )
    data_manager_ins.gpu_task.extend([].copy() for _ in range(settings.NUM_GPU))

    data_manager_ins.gpu_updated()


def start_gpu_monitor_all() -> None:
    init_global_gpu_var()

    if settings.NUM_GPU == 0:
        logger.warning("No GPU detected, GPU monitor will not start.")
        return

    nvidia_monitor = NvidiaMonitor(settings.NUM_GPU)
    nvidia_monitor.start_monitor(nvidia_monitor.gpu_monitor_thread)


if __name__ == "__main__":
    start_gpu_monitor_all()
