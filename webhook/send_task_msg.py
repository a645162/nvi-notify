from typing import Dict

from nvitop import Device

from config.config import (
    delay_send_seconds,
    get_emoji,
    local_ip,
    local_ipv6,
    server_name,
    web_host,
    web_server_port,
)
from utils.time_utils import get_now_time
from webhook.wework import send_text_normal, send_text_warning

num_gpu = Device.count()


def start_gpu_monitor(gpu_id, all_tasks_msg_dict, all_process_info: Dict):
    gpu_name = f"GPU:{gpu_id}" if num_gpu > 1 else "GPU"
    gpu_server_info = f"[{gpu_name}]" if num_gpu > 1 else gpu_name
    all_tasks_msg = "".join(all_tasks_msg_dict.values())

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
        handle_normal_text(
            f"{gpu_server_info}监控启动\n"
            f"{get_emoji('呲牙')*len(all_process_info)}{gpu_name}"
            f"上正在运行{len(all_process_info)}个任务：\n"
            f"{all_tasks_msg}\n"
            f"🌀{gpu_name}核心占用: {gpu_status['gpu_usage']}%\n"
            f"🌀{gpu_name}显存占用: {gpu_status['gpu_mem_usage']}/{gpu_status['gpu_mem_total']} "
            f"({gpu_status['gpu_mem_percent']}%)，{gpu_status['gpu_mem_free']}空闲\n",
        )


def send_gpu_task_message(process_info: Dict, task_status: str):
    gpu_name = f"GPU:{process_info['gpu_id']}" if num_gpu > 1 else "GPU"
    gpu_server_info = f"[{gpu_name}]\n" if num_gpu > 1 else ""
    all_tasks_msg = get_now_all_task_info(process_info, task_status)

    if not process_info["is_debug"]:
        if task_status == "create":
            handle_normal_text(
                f"{gpu_server_info}🚀{process_info['user']['name']}的"
                f"({process_info['project_name']}-{process_info['python_file']})启动\n"
                f"🌀{gpu_name}核心占用: {process_info['gpu_status']['gpu_usage']}%\n"
                f"🌀{gpu_name}显存占用: {process_info['gpu_status']['gpu_mem_usage']}/{process_info['gpu_status']['gpu_mem_total']} ({process_info['gpu_status']['gpu_mem_percent']}%)，{process_info['gpu_status']['gpu_mem_free']}空闲\n\n"
                f"{get_emoji('呲牙') * process_info['num_task']}{gpu_name}上正在运行{process_info['num_task']}个任务：\n"
                f"{all_tasks_msg}",
            )
        elif task_status == "finish":
            handle_normal_text(
                f"{gpu_server_info}☑️{process_info['user']['name']}的"
                f"({process_info['project_name']}-{process_info['python_file']})完成，"
                f"用时{process_info['running_time_human']}\n"
                f"🌀{gpu_name}核心占用: {process_info['gpu_status']['gpu_usage']}%\n"
                f"🌀{gpu_name}显存占用: {process_info['gpu_status']['gpu_mem_usage']}/{process_info['gpu_status']['gpu_mem_total']} ({process_info['gpu_status']['gpu_mem_percent']}%)，{process_info['gpu_status']['gpu_mem_free']}空闲\n\n"
                f"{get_emoji('呲牙') * (process_info['num_task'] - 1)}{gpu_name}上正在运行{process_info['num_task'] - 1}个任务：\n"
                f"{all_tasks_msg}",
                mentioned_id=process_info["user"]["mention_id"],
                mentioned_mobile=process_info["user"]["mention_phone_number"],
            )


def create_task_log(process_info: Dict):
    with open("./logging/log.log", "a") as f:
        output_log = (
            f"[{get_now_time()}]"
            f"[GPU:{process_info['gpu_id']}] {process_info['user']['name']} create new "
            f"{'debug ' if process_info['is_debug'] else ''}task: {process_info['pid']}"
        )
        f.write(output_log + "\n")
        print(output_log)


def finish_task_log(process_info: Dict):
    with open("./logging/log.log", "a") as f:
        output_log = (
            f"[{get_now_time()}]"
            f"[GPU:{process_info['gpu_id']}] finish {process_info['user']['name']}'s "
            f"{'debug ' if process_info['is_debug'] else ''}task: {process_info['pid']}，用时{process_info['running_time_human']}"
        )
        f.write(output_log + "\n")
        print(output_log)


def handle_normal_text(msg: str, mentioned_id=None, mentioned_mobile=None):
    if web_host is None:
        msg += f"📈详情: http://{local_ip}\n"
        # msg += f"http://[{local_ipv6}]\n"
    else:
        msg += f"📈详情: http://{web_host}\n"

    msg += f"⏰{get_now_time()}"
    send_text_normal(msg, mentioned_id, mentioned_mobile)


def handle_warning_text(msg: str) -> str:
    msg += f"http://{local_ip}\n"
    msg += f"http://[{local_ipv6}]\n"
    msg += f"⏰{get_now_time()}"
    return msg


def send_process_except_warning_msg():
    warning_message = f"⚠️⚠️{server_name}获取进程失败！⚠️⚠️\n"
    send_text_warning(msg=handle_warning_text(warning_message))


def send_cpu_except_warning_msg(cpu_id: int):
    warning_message = f"⚠️⚠️{server_name}获取CPU:{cpu_id}温度失败！⚠️⚠️\n"
    send_text_warning(msg=handle_warning_text(warning_message))


def send_cpu_temperature_warning_msg(cpu_id: int, cpu_temperature: float):
    warning_message = f"🤒🤒{server_name}的CPU:{cpu_id}温度已达{cpu_temperature}°C\n"
    send_text_warning(msg=handle_warning_text(warning_message))


def get_now_all_task_info(process_info: Dict, task_status: str):
    all_tasks_msg_dict = process_info["gpu_all_tasks_msg"]
    if task_status == "finish":
        del all_tasks_msg_dict[process_info["pid"]]
    all_tasks_msg = "".join(all_tasks_msg_dict.values())

    return all_tasks_msg
