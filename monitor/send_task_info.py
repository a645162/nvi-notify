from typing import Dict

from nvitop import Device

from config import config
from utils import ip, my_time
from webhook import wework

local_ip = ip.get_local_ip()
web_server_port = config.web_server_port
server_name = config.server_name
delay_send_seconds = config.delay_send_seconds
num_gpu = Device.count()


def start_gpu_monitor(gpu_id, all_tasks_msg, all_process_info: Dict):
    gpu_name = f"GPU:{gpu_id}"

    gpu_status = None
    send_start_info = False

    for process in all_process_info.values():
        if (
            process.running_time_in_seconds > delay_send_seconds
            and not process.is_debug
        ):
            gpu_status = process.gpu_status
            send_start_info = True

    if send_start_info:
        send_text_to_wework(
            f"{gpu_name}监控启动\n"
            f"{config.get_emoji('呲牙')*len(all_process_info)}{gpu_name}"
            f"上正在运行{len(all_process_info)}个任务：\n"
            f"{all_tasks_msg}\n"
            f"🌀{gpu_name}核心占用: {gpu_status['gpu_usage']}%\n"
            f"🌀{gpu_name}显存占用: {gpu_status['gpu_mem_usage']}/{gpu_status['gpu_mem_total']} "
            f"({gpu_status['gpu_mem_percent']}%)，{gpu_status['gpu_mem_free']}空闲\n",
        )


def send_gpu_task_message(process_info: Dict, task_status: str):
    all_tasks_msg = process_info["gpu_all_tasks_msg"]
    gpu_name = f"GPU:{process_info['gpu_id']}"

    if num_gpu > 1:
        gpu_server_info = f"[{gpu_name}]\n"
    else:
        gpu_server_info = ""

    if not process_info["is_debug"]:
        if task_status == "create":
            send_text_to_wework(
                f"{gpu_server_info}🚀{process_info['user']['name']}的"
                f"({process_info['project_name']}-{process_info['python_file']})启动\n"
                f"🌀{gpu_name}核心占用: {process_info['gpu_status']['gpu_usage']}%\n"
                f"🌀{gpu_name}显存占用: {process_info['gpu_status']['gpu_mem_usage']}/{process_info['gpu_status']['gpu_mem_total']} ({process_info['gpu_status']['gpu_mem_percent']}%)，{process_info['gpu_status']['gpu_mem_free']}空闲\n\n"
                f"{config.get_emoji('呲牙')*process_info['num_task']}{gpu_name}上正在运行{process_info['num_task']}个任务：\n"
                f"{all_tasks_msg}",
            )
        elif task_status == "finish":
            send_text_to_wework(
                f"{gpu_server_info}☑️{process_info['user']['name']}的"
                f"({process_info['project_name']}-{process_info['python_file']})完成，"
                f"用时{process_info['running_time_human']}\n"
                f"🌀{gpu_name}核心占用: {process_info['gpu_status']['gpu_usage']}%\n"
                f"🌀{gpu_name}显存占用: {process_info['gpu_status']['gpu_mem_usage']}/{process_info['gpu_status']['gpu_mem_total']} ({process_info['gpu_status']['gpu_mem_percent']}%)，{process_info['gpu_status']['gpu_mem_free']}空闲\n\n"
                f"{config.get_emoji('呲牙')*process_info['num_task']}{gpu_name}上正在运行{process_info['num_task']}个任务：\n"
                f"{all_tasks_msg}",
                mentioned_id=process_info["user"]["mention_id"],
                mentioned_mobile=process_info["user"]["mention_phone_number"],
            )


def create_task_log(process_info: Dict):
    print(
        f"[GPU:{process_info['gpu_id']}] create new task:{process_info['pid']} "
        f"on GPU:{process_info['gpu_id']}"
    )


def finish_task_log(process_info: Dict):
    print(
        f"[GPU:{process_info['gpu_id']}] finish {process_info['user']['name']}'s task:"
        f"{process_info['pid']}"
    )


def send_text_to_wework(msg: str, mentioned_id=None, mentioned_mobile=None):
    msg = (
        f"{msg}"
        f"📈详情: http://{local_ip}:{web_server_port}/nvitop\n"
        f"⏰{my_time.get_now_time()}"
    )
    wework.send_text(msg, mentioned_id, mentioned_mobile)


def send_process_except_msg():
    warning_message = (
        f"⚠️⚠️{server_name}获取进程失败！⚠️⚠️\n"
        f"IP: {local_ip}\n"
        f"⏰{my_time.get_now_time()}"
    )
    wework.direct_send_text_warning(msg=warning_message)


def send_cpu_except_warning_msg(cpu_id: int):
    warning_message = (
        f"⚠️⚠️{server_name}获取CPU:{cpu_id}温度失败！⚠️⚠️\n"
        f"IP: {local_ip}\n"
        # f"⏰{my_time.get_now_time()}"
    )
    # wework.direct_send_text_warning(msg=warning_message)


def send_cpu_temperature_warning_msg(cpu_id: int, cpu_temperature: float):
    warning_message = (
        f"🤒🤒{server_name}的CPU:{cpu_id}温度已经超过{cpu_temperature}°C\n"
        f"IP: {local_ip}\n"
        # f"⏰{my_time.get_now_time()}"
    )
    # wework.direct_send_text_warning(msg=warning_message)
