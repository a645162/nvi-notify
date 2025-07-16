# -*- coding: utf-8 -*-
import sys
import time

from group_center.core.path import cleanup_unused_rt_files

from config.settings import (
    GPU_MONITOR_SAMPLING_INTERVAL,
    MAX_CONSECUTIVE_ZERO_COUNT,
    NUM_GPU,
    WEBHOOK_SEND_LAUNCH_MESSAGE,
    CPU_CONSECUTIVE_ZERO_ENABLE,
    GPU_CONSECUTIVE_ZERO_ENABLE,
    SERVER_NAME,
    SERVER_NAME_SHORT,
)
from feature.group_center import message
from feature.group_center.data_manager import DataManager

from feature.monitor.gpu.gpu import GPU
from feature.monitor.gpu.gpu_process import GPUProcessInfo

from feature.monitor.monitor import Monitor
from feature.monitor.monitor_enum import AllWebhookName, MsgType

from feature.database.sqlite import get_sql

from feature.utils.logs import get_logger

from feature.webhook.msg_handler import MessageHandler
from feature.webhook.webhook import Webhook

logger = get_logger()
sql = get_sql()


class NvidiaMonitor(Monitor):
    def __init__(self, num_gpu: int):
        super().__init__("GPU")
        self.num_gpu = num_gpu
        self.is_multi_gpu_machine: bool = num_gpu > 1
        self.monitor_launch_flag = True
        self.total_num_task = 0

        self.gpu_obj_dict: dict[int, GPU] = self.get_gpu_obj()

        from feature.monitor.gpu.gpu_process import GPUProcessInfo

        self.all_processes: dict[int, GPUProcessInfo] = {}

        # GPU占用率监控历史记录
        self.process_gpu_usage_history: dict[int, GPUProcessInfo] = {}

    def get_gpu_obj(self) -> dict[int, GPU]:
        gpu_dict = {}
        for idx in range(NUM_GPU):
            gpu_dict[idx] = GPU(idx, self.is_multi_gpu_machine)

        return gpu_dict

    def gpu_monitor_thread(self):
        while self.monitor_thread_work:
            self.total_num_task = 0
            for idx, gpu in self.gpu_obj_dict.items():
                gpu.update()
                self.total_num_task += gpu.num_task
                self.all_processes.update(gpu.processes)

                # 监控GPU占用率
                self.monitor_gpu_usage_for_processes(gpu.processes)

                # Get gpu status info for webhook msg
                if sys.gettrace() or not self.monitor_launch_flag:
                    continue

                # Send to Group Center
                message.gpu_monitor_start(idx)
                sql.check_finish_task(gpu.processes, idx)

            # 每次都是要清空，下一轮会重新创建对象
            self.all_processes.clear()

            if self.should_send_monitor_launch_msg:
                self.send_gpu_monitor_launch_msg()

            # Cleanup
            cleanup_unused_rt_files()

            time.sleep(GPU_MONITOR_SAMPLING_INTERVAL)

    def monitor_gpu_usage_for_processes(
        self, current_processes: dict[int, "GPUProcessInfo"]
    ):
        """监控进程的GPU和CPU占用率，检测连续零占用率"""
        for pid, process_info in current_processes.items():
            # 获取GPU和CPU利用率
            process_info.get_gpu_utilization()
            process_info.get_cpu_utilization()

            # 如果历史记录中存在该进程，更新连续零占用率计数
            if pid in self.process_gpu_usage_history:
                historical_process = self.process_gpu_usage_history[pid]

                # 将历史计数传递给当前进程
                if GPU_CONSECUTIVE_ZERO_ENABLE:
                    process_info.consecutive_zero_gpu_count = (
                        historical_process.consecutive_zero_gpu_count
                    )
                    process_info.should_send_gpu_alert = (
                        historical_process.should_send_gpu_alert
                    )
                    process_info.already_has_alerted_zero_gpu_usage = (
                        historical_process.already_has_alerted_zero_gpu_usage
                    )
                    process_info.total_gpu_zero_alert_count = (
                        historical_process.total_gpu_zero_alert_count
                    )

                if CPU_CONSECUTIVE_ZERO_ENABLE:
                    process_info.consecutive_zero_cpu_count = (
                        historical_process.consecutive_zero_cpu_count
                    )
                    process_info.should_send_cpu_alert = (
                        historical_process.should_send_cpu_alert
                    )
                    process_info.already_has_alerted_zero_cpu_usage = (
                        historical_process.already_has_alerted_zero_cpu_usage
                    )
                    process_info.total_cpu_zero_alert_count = (
                        historical_process.total_cpu_zero_alert_count
                    )

            # 检查是否需要发送零占用率报警
            alert_info = process_info.should_send_zero_usage_alert()

            # 只有当CPU和GPU都需要报警时才发送（如果相应开关都启用）
            should_send_combined_alert = self._should_send_combined_alert(alert_info)

            if should_send_combined_alert:
                self.send_combined_zero_usage_alert(process_info, alert_info)

            # 更新历史记录
            self.process_gpu_usage_history[pid] = process_info

        # 清理已结束进程的历史记录
        self.cleanup_finished_processes(current_processes)

    def cleanup_finished_processes(
        self, current_processes: dict[int, "GPUProcessInfo"]
    ):
        """清理已结束进程的GPU占用率历史记录"""
        from feature.utils.process import check_process_exists

        finished_pids = []
        for pid in self.process_gpu_usage_history.keys():
            if pid not in current_processes or not check_process_exists(pid):
                finished_pids.append(pid)

        for pid in finished_pids:
            del self.process_gpu_usage_history[pid]

    @staticmethod
    def calculate_zero_time_str(count: int) -> str:
        """根据计数计算总共为0的时间"""
        total_seconds = GPU_MONITOR_SAMPLING_INTERVAL * count

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
        total_seconds = GPU_MONITOR_SAMPLING_INTERVAL * MAX_CONSECUTIVE_ZERO_COUNT

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
        gpu_alert_needed = alert_info["should_send_gpu_alert"]
        cpu_alert_needed = alert_info["should_send_cpu_alert"]

        # 检查启用的监控项
        gpu_enabled = GPU_CONSECUTIVE_ZERO_ENABLE
        cpu_enabled = CPU_CONSECUTIVE_ZERO_ENABLE

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
        self, process_info: "GPUProcessInfo", alert_info: dict
    ):
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
                    f"检测间隔: {self.get_detection_interval_str()}\n",
                ]
            )

            # 添加具体的占用率信息和统计信息
            if GPU_CONSECUTIVE_ZERO_ENABLE and alert_info["should_send_gpu_alert"]:
                # 使用报警次数乘以检测间隔计算总时间
                gpu_total_zero_time = self.calculate_zero_time_str(
                    process_info.total_gpu_zero_alert_count
                    * process_info.max_consecutive_zero_count
                )
                alert_msg_parts.append(
                    f"当前进程GPU占用率: {process_info.gpu_utilization:.1f}%\n"
                )
                alert_msg_parts.append(
                    f"GPU零占用计次: {process_info.total_gpu_zero_alert_count}\n"
                )
                alert_msg_parts.append(f"GPU总共0%时间: {gpu_total_zero_time}\n")

            if CPU_CONSECUTIVE_ZERO_ENABLE and alert_info["should_send_cpu_alert"]:
                # 使用报警次数乘以检测间隔计算总时间
                cpu_total_zero_time = self.calculate_zero_time_str(
                    process_info.total_cpu_zero_alert_count
                    * process_info.max_consecutive_zero_count
                )
                alert_msg_parts.append(
                    f"当前进程CPU占用率: {process_info.cpu_percent:.1f}%\n"
                )
                alert_msg_parts.append(
                    f"CPU零占用计次: {process_info.total_cpu_zero_alert_count}\n"
                )
                alert_msg_parts.append(f"CPU总共0%时间: {cpu_total_zero_time}\n")

            alert_msg_parts.extend(
                [
                    f"已经运行: {process_info.running_time_human}\n\n",
                    f"报警时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n",
                ]
            )

            alert_msg = "".join(alert_msg_parts)
            msg = MessageHandler.handle_normal_text(alert_msg)

            # 发送到 webhook
            Webhook.enqueue_msg_to_webhook(
                msg, MsgType.NORMAL, enable_webhook_name=AllWebhookName.ALL
            )

            # 通过 group_center发送到群组
            from group_center.core.feature.custom_client_message import (
                machine_message_directly,
            )

            # Send to lark by Group Center
            machine_message_directly(
                server_name=SERVER_NAME,
                server_name_eng=SERVER_NAME_SHORT,
                content=msg,
                at=process_info.user.name_cn if process_info.user else "",
            )

            # 通过 group_center 发送给用户
            if process_info.user and process_info.user.name_cn:
                from group_center.core.feature.custom_client_message import (
                    machine_user_message_directly,
                )

                machine_user_message_directly(
                    user_name=process_info.user.name_cn, content=msg
                )

            logger.warning(
                f"Combined zero usage alert sent for process {process_info.pid} (GPU count: {process_info.total_gpu_zero_alert_count}, CPU count: {process_info.total_cpu_zero_alert_count})"
            )

            # 发送成功后，重置当前报警标志，准备下一轮检测
            if GPU_CONSECUTIVE_ZERO_ENABLE and alert_info["should_send_gpu_alert"]:
                process_info.should_send_gpu_alert = False

            if CPU_CONSECUTIVE_ZERO_ENABLE and alert_info["should_send_cpu_alert"]:
                process_info.should_send_cpu_alert = False

        except Exception as e:
            logger.error(f"Failed to send combined zero usage alert: {e}")

    def _should_send_combined_alert_dummy_check(
        self, process_info: "GPUProcessInfo"
    ) -> bool:
        """
        综合报警发送前的dummy检测逻辑
        """
        # 示例条件（可以根据需要修改）：
        # 1. 检查进程是否是调试模式
        if hasattr(process_info, "is_debug") and process_info.is_debug:
            return False

        # 2. 检查运行时间是否足够长
        if process_info.running_time_in_seconds < 300:  # 5分钟
            return False

        # 3. 检查是否是忽略的任务
        if process_info.ignore_task:
            return False

        # 4. 其他自定义条件...

        return True

    def send_zero_cpu_usage_alert(self, process_info: "GPUProcessInfo"):
        """发送CPU零占用率报警（已废弃，请使用综合报警）"""
        logger.warning(
            "send_zero_cpu_usage_alert is deprecated, use send_combined_zero_usage_alert instead"
        )

    def send_zero_gpu_usage_alert(self, process_info: "GPUProcessInfo"):
        """发送GPU零占用率报警（已废弃，请使用综合报警）"""
        logger.warning(
            "send_zero_gpu_usage_alert is deprecated, use send_combined_zero_usage_alert instead"
        )

    def _should_send_gpu_alert_dummy_check(
        self, process_info: "GPUProcessInfo"
    ) -> bool:
        """
        GPU报警发送前的dummy检测逻辑（已废弃）
        """
        return self._should_send_combined_alert_dummy_check(process_info)

    def _should_send_cpu_alert_dummy_check(
        self, process_info: "GPUProcessInfo"
    ) -> bool:
        """
        CPU报警发送前的dummy检测逻辑（已废弃）
        """
        return self._should_send_combined_alert_dummy_check(process_info)

    @property
    def should_send_monitor_launch_msg(self):
        if not self.monitor_launch_flag:
            return False
        else:
            self.monitor_launch_flag = False
        return WEBHOOK_SEND_LAUNCH_MESSAGE and self.total_num_task > 0

    def send_gpu_monitor_launch_msg(self):
        launch_msg_text = []

        for gpu in self.gpu_obj_dict.values():
            gpu.get_all_tasks_msg_body()
            launch_msg_text.append(
                "\n"
                + gpu.gpu_tasks_num_msg_header
                + gpu.all_tasks_msg_body
                + gpu.gpu_status_msg
            )

        if len(launch_msg_text) > 0:
            msg = MessageHandler.handle_normal_text(
                "GPU监控启动" + "".join(launch_msg_text)
            )
            Webhook.enqueue_msg_to_webhook(
                msg, MsgType.NORMAL, enable_webhook_name=AllWebhookName.ALL
            )


def init_global_gpu_var():
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

    DataManager().gpu_info.extend(default_gpu_info_dict.copy() for _ in range(NUM_GPU))
    DataManager().gpu_usage.extend(
        default_gpu_usage_dict.copy() for _ in range(NUM_GPU)
    )
    DataManager().gpu_task.extend([].copy() for _ in range(NUM_GPU))

    DataManager().gpu_updated()


def start_gpu_monitor_all():
    init_global_gpu_var()

    if NUM_GPU == 0:
        logger.warning("No GPU detected, GPU monitor will not start.")
        return

    nvidia_monitor = NvidiaMonitor(NUM_GPU)
    nvidia_monitor.start_monitor(nvidia_monitor.gpu_monitor_thread)


if __name__ == "__main__":
    start_gpu_monitor_all()
