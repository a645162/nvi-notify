from nvitop import *
import threading
import time

from utils import my_time
from webhook import wework

from config import config, keywords 

threshold = config.gpu_monitor_usage_threshold
sleep_time = config.gpu_monitor_sleep_time
user_list = config.user_list


def send_text_to_wework(msg: str, mentioned_id=None, mentioned_mobile=None):
    now_time = my_time.get_now_time()
    send_text = \
        (
            f"{msg}"
            f"发送时间: {now_time}"
        )
    wework.send_text(send_text, mentioned_id, mentioned_mobile)


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
    print(f"{gpu_name} start create new task:{pid}")

    if running_tasks[pid]['debug'] is None:
        send_text_to_wework(
            f"[{gpu_name}启动]{running_tasks[pid]['user']['name']}新任务({get_command_py_files(running_tasks[pid])})已启动。\n"
            f"\t{gpu_name}占用：{gpu_usage}%，空闲显存：{gpu_mem_free}\n"
            f"\t{gpu_name}显存情况：{gpu_mem_usage}/{gpu_mem_total} ({gpu_mem_percent}%)\n"
            f"{gpu_name}上正在运行{len(running_tasks)}个任务：\n"
            f"\t{all_tasks_msg}",
            mentioned_id=running_tasks[pid]['user']['mention_id'],
            mentioned_mobile=running_tasks[pid]['user']['mention_phone_number']
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
        user_dict = fininshed_task['user']
        user_name = user_dict['name']
        mention_id_list = user_dict['mention_id']
        mention_mobile_list = user_dict['mention_phone_number']

        send_text_to_wework(
            f"[{gpu_name}完成]{user_name}的任务({get_command_py_files(fininshed_task)})已完成，用时{fininshed_task['running_time']}。\n"
            f"\t{gpu_name}占用：{gpu_usage}%，空闲显存：{gpu_mem_free}\n"
            f"\t{gpu_name}显存情况：{gpu_mem_usage}/{gpu_mem_total} ({gpu_mem_percent}%)\n"
            f"{gpu_name}上正在运行{len(running_tasks)}个任务：\n"
            f"{all_tasks_msg}",
            mentioned_id=mention_id_list,
            mentioned_mobile=mention_mobile_list
        )


def get_command_py_files(task_info: dict):
    cmdline = task_info["cmdline"]
    for cmd_str in cmdline:
        if cmd_str.lower().endswith(".py"):
            if "/" in cmd_str:
                cmd_list = cmd_str.split("/")
                return(f"{cmd_list[-2]}/{cmd_list[-1]}")
            else:
                return cmd_str


def get_all_tasks_msg(tasks_info: dict):
    all_tasks_msg = []
    for task_idx, info in enumerate(tasks_info.values()):
        debug_info = '调试' if info['debug'] is not None else ''
        task_msg = (f"\t{debug_info}任务{task_idx}  用户：{info['user']['name']}  "
                    f"显存占用：{info['memory_usage']}  "
                    f"运行时长：{info['running_time']}  \n")
        all_tasks_msg.append(task_msg)

    return ''.join(all_tasks_msg)


class nvidia_monitor:
    gpu_id: int

    def __init__(self, gpu_id):
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
                
                user_dict = keywords.find_user_by_path(config.user_list, gpu_process.cwd())
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
                    "command": gpu_process.command(),
                    "cmdline": gpu_process.cmdline(),
                    "running_time_second": gpu_process.running_time_in_seconds(),
                    "running_time": gpu_process.running_time_human(),
                    "debug": debug_flag,
                }

        return gpu_tasks_info

    def get_gpu_all_processes(self):
        return self.nvidia_i.processes()

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
            print(f"GPU {self.gpu_id} threshold is {threshold}")

            last_running_tasks = None
            while monitor_thread_work:
                running_tasks = self.get_valid_gpu_tasks()

                if last_running_tasks and running_tasks.keys() != last_running_tasks.keys():
                    new_task_pid = set(running_tasks.keys()) - set(last_running_tasks.keys())
                    finished_task_pid = set(last_running_tasks.keys()) - set(running_tasks.keys())

                    gpu_util = self.get_gpu_utl()
                    gpu_mem_usage = self.get_gpu_mem_usage()
                    gpu_mem_free = self.get_gpu_mem_free()
                    gpu_mem_percent = self.get_gpu_mem_percent()
                    gpu_mem_total = self.get_gpu_mem_total()

                    for pid in new_task_pid:
                        gpu_create_task(
                            pid,
                            running_tasks,
                            gpu_util,
                            gpu_mem_usage,
                            gpu_mem_free,
                            gpu_mem_percent,
                            gpu_mem_total
                        )

                    for pid in finished_task_pid:
                        gpu_finish_task(
                            pid,
                            last_running_tasks[pid],
                            running_tasks,
                            gpu_util,
                            gpu_mem_usage,
                            gpu_mem_free,
                            gpu_mem_percent,
                            gpu_mem_total
                        )

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
    # Get GPU count
    gpu_count = Device.count()

    for i in range(gpu_count):
        nvidia_monitor_i = nvidia_monitor(i)
        # print(nvidia_monitor_i.get_gpu_usage())
        nvidia_monitor_i.start_monitor()


if __name__ == "__main__":
    start_monitor_all()
