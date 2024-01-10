import threading
import time
from typing import List

import psutil
from nvitop import *

from config import config, keywords
from utils import my_time
from webhook import wework
from web.ipaddr_simple import get_local_ip

local_ip = config.local_ip
server_name = config.server_name
sleep_time = config.gpu_monitor_sleep_time
web_server_port = config.web_server_port
user_list = config.user_list


def send_text_to_wework(msg: str, mentioned_id=None, mentioned_mobile=None):
    now_time = my_time.get_now_time()
    send_text = \
        (
            f"{msg}"
            f"📈详情: http://{local_ip}:{web_server_port}/nvitop1\n"
            f"⏰{now_time}"
        )
    wework.send_text(send_text, mentioned_id, mentioned_mobile)


def delay_send_create_task_msg(
        new_task_pid: List,
        finished_task_pid: List,
        running_tasks: dict,
        gpu_staus: dict,
        task_start_times: dict,
        temp_running_times: dict,
):

    ignore_pid = 0
    for pid in new_task_pid:
        print(f"GPU:{running_tasks[pid]['device']} start create new task:{pid}")
        running_time = running_tasks[pid]["running_time_second"]
        if len(task_start_times) == 0:
            task_start_times = {pid: running_time}
            temp_running_times = {pid: running_time}
        else:
            task_start_times[pid] = running_time
            temp_running_times[pid] = running_time

    for pid in task_start_times.keys():
        if pid in running_tasks:
            if task_start_times[pid] > 30:
                gpu_create_task(pid, running_tasks, **gpu_staus)
                ignore_pid = pid
            else:
                temp_running_times[pid] = running_tasks[pid]["running_time_second"]
        if pid in finished_task_pid:
            ignore_pid = pid

    task_start_times.update(temp_running_times)

    if ignore_pid > 0:
        task_start_times.pop(ignore_pid, None)
        temp_running_times.pop(ignore_pid, None)
        ignore_pid = 0

    return task_start_times, temp_running_times


def gpu_create_task(
        pid: int,
        running_tasks: dict,
        gpu_usage: int,
        gpu_mem_usage: str,
        gpu_mem_free: str,
        gpu_mem_percent: float,
        gpu_mem_total: str
):
    all_tasks_msg = get_all_tasks_msg(running_tasks)
    gpu_name = f"GPU:{running_tasks[pid]['device']}"

    if running_tasks[pid]['debug'] is None: # and running_tasks[pid]["running_time_second"] < 120:
        if num_gpu > 1:
            gpu_server_info = f"[{gpu_name}]\n"
        else:
            gpu_server_info = ""
        send_text_to_wework(
            f"{gpu_server_info}🚀{running_tasks[pid]['user']['name']}的"
            f"({running_tasks[pid]['project_name']}-{get_command_py_files(running_tasks[pid])})启动\n"
            f"🌀{gpu_name}核心占用: {gpu_usage}%\n"
            f"🌀{gpu_name}显存占用: {gpu_mem_usage}/{gpu_mem_total} ({gpu_mem_percent}%)，{gpu_mem_free}空闲\n\n"
            f"{config.get_emoji('呲牙')*len(running_tasks)}{gpu_name}上正在运行{len(running_tasks)}个任务：\n"
            f"{all_tasks_msg}",
            # mentioned_id=running_tasks[pid]['user']['mention_id'],
            # mentioned_mobile=running_tasks[pid]['user']['mention_phone_number']
        )


def gpu_finish_task(
        pid: int,
        fininshed_task: dict,
        running_tasks: dict,
        gpu_usage: int,
        gpu_mem_usage: str,
        gpu_mem_free: str,
        gpu_mem_percent: float,
        gpu_mem_total: str
):
    all_tasks_msg = get_all_tasks_msg(running_tasks)

    gpu_name = f"GPU:{fininshed_task['device']}"
    print(f"{gpu_name} finish task:{pid}")

    if fininshed_task["debug"] is None and fininshed_task["running_time_second"] > 300:
        if num_gpu > 1:
            gpu_server_info = f"[{gpu_name}]\n"
        else:
            gpu_server_info = ""

        user_dict = fininshed_task['user']
        user_name = user_dict['name']
        mention_id_list = user_dict['mention_id']
        mention_mobile_list = user_dict['mention_phone_number']

        send_text_to_wework(
            f"{gpu_server_info}☑️{user_name}的"
            f"({fininshed_task['project_name']}-{get_command_py_files(fininshed_task)})完成，"
            f"用时{fininshed_task['running_time']}\n"
            f"🌀{gpu_name}核心占用: {gpu_usage}%\n"
            f"🌀{gpu_name}显存占用: {gpu_mem_usage}/{gpu_mem_total} ({gpu_mem_percent}%)，{gpu_mem_free}空闲\n\n"
            f"{config.get_emoji('呲牙')*len(running_tasks)}{gpu_name}上正在运行{len(running_tasks)}个任务：\n"
            f"{all_tasks_msg}",
            mentioned_id=mention_id_list,
            mentioned_mobile=mention_mobile_list
        )


def get_command_py_files(task_info: dict):
    cmdline = task_info["cmdline"]
    for cmd_str in cmdline:
        if cmd_str.lower().endswith(".py"):
            if "/" in cmd_str:
                return cmd_str.split("/")[-1]
            else:
                return cmd_str  # cmd_str[:-3] # remove file expanded-name


def get_all_tasks_msg(tasks_info: dict):
    all_tasks_msg = []
    for task_idx, info in enumerate(tasks_info.values()):
        debug_info = '🐞' if info['debug'] is not None else ''
        task_msg = (f"{config.get_emoji(task_idx)}{debug_info}"
                    f"用户: {info['user']['name']}  "
                    f"显存占用: {info['memory_usage']}  "
                    f"运行时长: {info['running_time']}\n")
        all_tasks_msg.append(task_msg)

    return ''.join(all_tasks_msg)


class nvidia_monitor:

    def __init__(self, gpu_id: int):
        self.gpu_id = gpu_id
        self.thread = None
        self.nvidia_i = None
        self.update_device()

    def update_device(self):
        self.nvidia_i = Device(self.gpu_id)

    def get_valid_gpu_tasks(self):
        gpu_tasks_info = {}
        for pid, gpu_process in self.get_gpu_all_processes().items():
            process_name = gpu_process.name()

            if process_name == "python":
                debug_flag = keywords.is_debug_process(gpu_process.cmdline())
                user_dict = keywords.find_user_by_path(
                    config.user_list, self.get_gpu_process_cmd(gpu_process) + '/')

                if user_dict is None:
                    user_dict={
                        "name": "Unknown",
                        "keywords": [],
                        "mention_id": [],
                        "mention_phone_number": []
                    }

                gpu_tasks_info[pid] = {
                    "device": self.gpu_id,
                    "user": user_dict,
                    "memory_usage": gpu_process.gpu_memory_human(),
                    "project_name": self.get_gpu_process_cmd(gpu_process).split('/')[-1],
                    "command": gpu_process.command(),
                    "cmdline": gpu_process.cmdline(),
                    "running_time_second": gpu_process.running_time_in_seconds(),
                    "running_time": gpu_process.running_time_human(),
                    "debug": debug_flag,
                }

        return gpu_tasks_info

    def get_gpu_all_processes(self):
        try:
            return self.nvidia_i.processes()
        except:
            warning_message = (
                    f"⚠️⚠️⚠️{server_name}获取进程失败！⚠️⚠️⚠️\n"
                    f"IP: {local_ip}"
                    f"⏰{my_time.get_now_time()}"
                )
            wework.direct_send_text_warning(msg=warning_message)

    def get_gpu_process_cmd(self, process: GpuProcess) -> str:
        try:
            return process.cwd()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            warning_message = (
                    f"⚠️⚠️⚠️{server_name}获取进程失败！⚠️⚠️⚠️\n"
                    f"IP: {local_ip}"
                    f"⏰{my_time.get_now_time()}"
                )
            wework.direct_send_text_warning(msg=warning_message)

            return ""

    def get_gpu_utl(self):
        return self.nvidia_i.gpu_utilization()

    def get_gpu_mem_utl(self):
        return self.nvidia_i.memory_utilization()

    def get_gpu_mem_usage(self):
        return self.nvidia_i.memory_used_human()

    def get_gpu_mem_free(self):
        return self.nvidia_i.memory_free_human()

    def get_gpu_mem_percent(self):
        return self.nvidia_i.memory_percent()

    def get_gpu_mem_total(self):
        return self.nvidia_i.memory_total_human()

    monitor_thread_work = False

    def start_monitor(self):

        def monitor_thread():

            print(f"GPU {self.gpu_id} monitor start")

            finished_task_pid, new_task_pid = [], []
            last_running_tasks = {}
            task_start_times = {}
            temp_running_times = {}
            while monitor_thread_work:
                running_tasks = self.get_valid_gpu_tasks()

                if len(running_tasks) == 0:
                    if len(last_running_tasks) > 0:
                        finished_task_pid = list(last_running_tasks.keys())
                    else:
                        finished_task_pid, new_task_pid = [], []
                else:
                    if len(last_running_tasks) == 0:
                        new_task_pid = list(running_tasks.keys())
                    else:
                        new_task_pid = list(
                            set(running_tasks.keys()) - set(last_running_tasks.keys()))
                        finished_task_pid = list(
                            set(last_running_tasks.keys()) - set(running_tasks.keys()))

                gpu_staus = {
                    'gpu_usage': self.get_gpu_utl(),
                    'gpu_mem_usage' : self.get_gpu_mem_usage(),
                    'gpu_mem_free' : self.get_gpu_mem_free(),
                    'gpu_mem_percent': self.get_gpu_mem_percent(),
                    'gpu_mem_total' : self.get_gpu_mem_total(),
                }

                task_start_times, temp_running_times = delay_send_create_task_msg(
                    new_task_pid,
                    finished_task_pid,
                    running_tasks,
                    gpu_staus,
                    task_start_times,
                    temp_running_times
                )

                for pid in finished_task_pid:
                    if pid not in last_running_tasks.keys():
                        continue
                    gpu_finish_task(pid, last_running_tasks[pid], running_tasks,**gpu_staus)

                last_running_tasks = running_tasks
                time.sleep(sleep_time)

            print(f"GPU {self.gpu_id} monitor stop")

        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=monitor_thread)
        monitor_thread_work = True
        self.thread.start()
        # self.thread.join()

    def stop_monitor(self):
        monitor_thread_work = False
        if self.thread is not None and self.thread.is_alive():
            self.thread.join()


def start_monitor_all():
    global num_gpu
    # Get GPU count
    num_gpu = Device.count()

    for idx in range(num_gpu):
        nvidia_monitor_idx = nvidia_monitor(idx)
        # print(nvidia_monitor_i.get_gpu_usage())
        nvidia_monitor_idx.start_monitor()


if __name__ == "__main__":
    start_monitor_all()
