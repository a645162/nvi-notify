import copy

from nvitop import Device
from nvitop.api.process import GpuProcess
from nvitop.api.utils import NaType

from config.settings import WEBHOOK_DELAY_SEND_SECONDS
from feature.global_variable.gpu import (
    global_gpu_info,
    global_gpu_task,
    global_gpu_usage,
    global_variable_gpu_updated
)
from feature.monitor.gpu.gpu_process import GPUProcessInfo
from feature.monitor.gpu.task.for_webhook import TaskInfoForWebHook
from feature.monitor.monitor_enum import TaskState
from feature.monitor.utils import Converter
from feature.webhook.msg_handler import MessageHandler
from feature.sql.sqlite import get_sql
from feature.utils.logs import get_logger

logger = get_logger()
sql = get_sql()


class GPU:
    def __init__(self, gpu_id: int, multi_gpu_machine_flag: bool):
        self.gpu_id = gpu_id
        self.is_multi_gpu_machine = multi_gpu_machine_flag

        self.processes: dict = {}
        self.nvidia_i: Device = Device(self.gpu_id)

        self._num_task: int = 0

        self.get_gpu_info()

    def update(self):
        self.update_global_gpu_status()
        self.update_all_processes_info()
        self.handle_death_processes()
        self.update_new_processes_info()
        self.update_global_gpu_task()

    def update_all_processes_info(self):
        for pid in self.processes:
            self.processes[pid].update_gpu_process_info()

    def handle_death_processes(self):
        tmp_process = copy.copy(self.processes)
        cur_gpu_all_processes = self.all_processes
        for pid in tmp_process:
            if pid in cur_gpu_all_processes:
                continue
            self.processes[pid].set_finish_time()
            self.get_all_tasks_msg_body_for_task_finish(pid)
            self.num_task -= 1
            self.processes[pid].state = TaskState.DEATH
            del self.processes[pid]
        del tmp_process

        self.get_all_tasks_msg_body()

    def update_new_processes_info(self):
        for pid, gpu_process in self.all_processes.items():
            if pid in self.processes:
                continue

            new_process = GPUProcessInfo(pid, self.gpu_id, gpu_process)
            if not new_process.is_python:
                continue

            if new_process.running_time_in_seconds > WEBHOOK_DELAY_SEND_SECONDS:
                new_process.state = TaskState.WORKING
            else:
                new_process.state = TaskState.NEWBORN

            new_process.gpu = self
            self.processes[pid] = new_process

        self.num_task: int = len(self.processes)

    @property
    def all_processes(self) -> dict[int, GpuProcess] | None:
        try:
            return self.nvidia_i.processes()
        except Exception as e:
            logger.error(e)
            MessageHandler.enqueue_except_warning_msg("process")

    @property
    def name(self) -> str:
        return self.nvidia_i.name()

    @property
    def name_short(self) -> str:
        current_str = self.name
        current_str_upper = self.name.upper()
        keywords = ["NVIDIA", "GeForce", "Quadro"]

        for keyword in keywords:
            keyword_upper = keyword.upper()
            while keyword_upper in current_str_upper:
                index = current_str_upper.index(keyword_upper)
                # 计算关键词在原始字符串中的起始位置
                index_original = current_str_upper[:index].count(" ") - current_str[
                                                                        :index
                                                                        ].count(" ")
                # 删除原始字符串中的关键词
                current_str = (
                        current_str[:index_original]
                        + current_str[index_original + len(keyword) + 1:]
                )
                current_str_upper = current_str.upper()
        return current_str.strip()

    @property
    def name_for_msg(self) -> str:
        if self.is_multi_gpu_machine:
            return f"[GPU:{self.gpu_id}]"
        else:
            return "GPU"

    @property
    def name_for_msg_header(self) -> str:
        if self.is_multi_gpu_machine:
            return f"[GPU:{self.gpu_id}]"
        else:
            return ""

    @property
    def num_task(self):
        return self._num_task

    @num_task.setter
    def num_task(self, value) -> None:
        self._num_task = value
        self.get_gpu_tasks_num_msg_header()

    @property
    def gpu_utilization(self) -> int | NaType:
        return self.nvidia_i.gpu_utilization()

    @property
    def memory_utilization(self) -> int | NaType:
        return self.nvidia_i.memory_utilization()

    @property
    def memory_used_human(self) -> str | NaType:
        return self.nvidia_i.memory_used_human()

    @property
    def memory_free_human(self) -> str | NaType:
        return self.nvidia_i.memory_free_human()

    @property
    def memory_percent(self) -> float | NaType:
        return self.nvidia_i.memory_percent()

    @property
    def memory_total(self) -> int | NaType:
        """Total GPU memory in `bytes`."""
        return self.nvidia_i.memory_total()

    @property
    def memory_total_human(self) -> str | NaType:
        return self.nvidia_i.memory_total_human()

    @property
    def power_usage(self) -> int:
        return int(round(self.nvidia_i.power_usage() / 1000, 0))

    @property
    def TDP(self) -> int:
        return int(round(self.nvidia_i.power_limit() / 1000, 0))

    @property
    def temperature(self) -> int:
        return self.nvidia_i.temperature()

    def get_gpu_tasks_num_msg_header(self):
        if self.num_task == 0:
            self.gpu_tasks_num_msg_header = f"{self.name_for_msg}当前无任务\n"
        else:
            self.gpu_tasks_num_msg_header = (
                f"{TaskInfoForWebHook.get_emoji('呲牙') * self.num_task}"
                f"{self.name_for_msg}上正在运行{self.num_task}个任务：\n"
            )

    @property
    def gpu_status_msg(self) -> str:
        return (
            f"🌀{self.name_for_msg}核心占用: {self.gpu_utilization}%\n"
            f"🌀{self.name_for_msg}显存占用: {self.memory_used_human}/{self.memory_total_human} "
            f"({self.memory_percent}%)，{self.memory_free_human}空闲\n"
        )

    def get_all_tasks_msg_body(self) -> None:
        """all tasks msg"""
        self.get_all_tasks_msg_body_for_task_finish(-1)

    def get_all_tasks_msg_body_for_task_finish(self, finished_pid: int):
        """all tasks that exclude finished msg"""
        all_tasks_msg_list = []
        task_idx = 0
        for pid, process in self.processes.items():
            if finished_pid == pid:
                continue
            all_tasks_msg_list.append(self.gen_task_msg_lite(task_idx, process))
            task_idx += 1

        self.all_tasks_msg_body = "".join(all_tasks_msg_list)

    @staticmethod
    def gen_task_msg_lite(task_idx: int, process: GPUProcessInfo) -> str:
        idx_emoji = TaskInfoForWebHook.get_emoji((task_idx))
        debug_emoji = "🐞" if process.is_debug else ""
        task_msg = (
            f"{idx_emoji}{debug_emoji}"
            f"用户: {process.user.name_cn}  "
            f"最大显存: {process.task_gpu_memory_max_human}  "
            f"运行时长: {process.running_time_human}\n"
        )

        return task_msg

    def get_gpu_info(self):
        try:
            if self.gpu_id not in global_gpu_info:
                global_gpu_info[self.gpu_id] = {}

            global_gpu_info[self.gpu_id].update(
                {
                    "gpuName": self.name_short,
                    "gpuTDP": self.TDP,

                }
            )

            global_variable_gpu_updated()
        except AttributeError as e:
            print(f"Error updating GPU info: Missing attribute {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def update_global_gpu_status(self):
        try:
            # 确保gpu_id对应的字典项存在
            if self.gpu_id not in global_gpu_usage:
                global_gpu_usage[self.gpu_id] = {}

            # 直接使用字典的update方法更新信息，同时添加异常处理
            global_gpu_usage[self.gpu_id].update(
                {
                    "coreUsage": self.gpu_utilization,
                    "memoryUsage": self.memory_percent,
                    "gpuMemoryTotalMB": Converter.convert_bytes_to_mb(
                        self.memory_total
                    ),
                    "gpuMemoryUsage": self.memory_used_human,
                    "gpuMemoryTotal": self.memory_total_human,
                    "gpuPowerUsage": self.power_usage,
                    "gpuTemperature": self.temperature,
                }
            )

            global_variable_gpu_updated()
        except AttributeError as e:
            print(f"Error updating GPU status: Missing attribute {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def update_global_gpu_task(self):
        # 在监视线程中就进行处理，哪怕这里阻塞了，也就是相当于多加一点延时
        current_gpu_tasks_list = list(self.processes.values()).copy()
        current_gpu_tasks_list.sort(key=lambda x: x.pid)

        global_gpu_task[self.gpu_id].clear()
        global_gpu_task[self.gpu_id].extend(current_gpu_tasks_list)
        global_variable_gpu_updated()
