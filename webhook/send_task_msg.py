import os
from pathlib import Path
from typing import Dict

from config.settings import (
    NUM_GPU,
    SERVER_DOMAIN,
    SERVER_NAME,
    WEBHOOK_DELAY_SEND_SECONDS,
    IPv4,
    IPv6,
    get_emoji,
    get_now_time,
)
from webhook.wework import send_text


def send_gpu_monitor_start_msg(gpu_id: int, all_process_info: Dict):
    """
    启动GPU监控函数
    :param gpu_id: GPU ID
    :param all_process_info: 所有进程信息字典
    """
    gpu_name = f"GPU:{gpu_id}" if NUM_GPU > 1 else "GPU"
    gpu_server_info = f"[{gpu_name}]" if NUM_GPU > 1 else gpu_name

    gpu_status = None
    send_start_info = False

    all_tasks_msg = ""

    for process in all_process_info.values():
        if (
            process.running_time_in_seconds > WEBHOOK_DELAY_SEND_SECONDS
            and not process.is_debug
        ):
            if process.is_multi_gpu and process.local_rank != 0:
                continue

            send_start_info = True
            gpu_status = process.gpu_status
            all_tasks_msg = "".join(process.gpu_all_tasks_msg.values())
            break

    if send_start_info:
        handle_normal_text(
            f"{gpu_server_info}监控启动\n"
            f"{get_emoji('呲牙') * len(all_process_info)}{gpu_name}"
            f"上正在运行{len(all_process_info)}个任务：\n"
            f"{all_tasks_msg}\n"
            f"🌀{gpu_name}核心占用: {gpu_status['gpu_usage']}%\n"
            f"🌀{gpu_name}显存占用: {gpu_status['gpu_mem_usage']}/{gpu_status['gpu_mem_total']} "
            f"({gpu_status['gpu_mem_percent']}%)，{gpu_status['gpu_mem_free']}空闲\n",
        )


def send_gpu_task_message(process_info: Dict, task_status: str):
    """
    发送GPU任务消息函数
    :param process_info: 进程信息字典
    :param task_status: 任务状态
    """
    gpu_name = f"GPU:{process_info['gpu_id']}" if NUM_GPU > 1 else "GPU"
    multi_gpu_idx = f"[{gpu_name}]\n" if NUM_GPU > 1 else ""

    gpu_info_msg = (
        f"🌀{gpu_name}核心占用: {process_info['gpu_status']['gpu_usage']}%\n"
        f"🌀{gpu_name}显存占用: {process_info['gpu_status']['gpu_mem_usage']}/{process_info['gpu_status']['gpu_mem_total']} ({process_info['gpu_status']['gpu_mem_percent']}%)，{process_info['gpu_status']['gpu_mem_free']}空闲\n\n"
        f"{get_emoji('呲牙') * (process_info['num_task'] - 1)}{gpu_name}上正在运行{process_info['num_task'] - 1}个任务：\n"
        f"{''.join(process_info['gpu_all_tasks_msg'].values())}"
    )
    if not process_info["is_debug"]:
        if task_status == "create":
            create_msg_header = f"{multi_gpu_idx}🚀{process_info['user']['name']}的({process_info['project_name']}-{process_info['python_file']})启动\n"
            handle_normal_text(msg=create_msg_header + gpu_info_msg)
        elif task_status == "finish":
            finish_msg_header = f"{multi_gpu_idx}☑️{process_info['user']['name']}的({process_info['project_name']}-{process_info['python_file']})完成，用时{process_info['running_time_human']}\n"
            handle_normal_text(
                msg=finish_msg_header + gpu_info_msg,
                mentioned_id=process_info["user"]["wework"]["mention_id"],
                mentioned_mobile=process_info["user"]["wework"]["mention_mobile"],
            )


def log_task_info(process_info: Dict, task_type: str):
    """
    任务日志函数
    :param process_info: 进程信息字典
    :task_type: 任务类型, `create` or `finish`
    """
    if task_type is None:
        raise ValueError("task_type is None")

    logfile_path = "./log"
    if not os.path.exists(logfile_path):
        os.makedirs(logfile_path)

    with open(Path(logfile_path // "log.log"), "a") as log_writer:
        if task_type == "create":
            output_log = f"[{get_now_time()}][GPU:{process_info['gpu_id']}] {process_info['user']['name']} create new {'debug ' if process_info['is_debug'] else ''}task: {process_info['pid']}\n"
        elif task_type == "finish":
            output_log = f"[{get_now_time()}][GPU:{process_info['gpu_id']}] finish {process_info['user']['name']}'s {'debug ' if process_info['is_debug'] else ''}task: {process_info['pid']}，用时{process_info['running_time_human']}\n"
        log_writer.write(output_log)
        print(output_log)


def handle_normal_text(msg: str, mentioned_id=None, mentioned_mobile=None):
    """
    处理普通文本消息函数
    :param msg: 消息内容
    :param mentioned_id: 提及的用户ID
    :param mentioned_mobile: 提及的用户手机号码
    """
    if SERVER_DOMAIN is None:
        msg += f"📈http://{IPv4}\n"
        # msg += f"http://[{IPv6}]\n"
    else:
        msg += f"📈http://{SERVER_DOMAIN}\n"

    msg += f"⏰{get_now_time()}"
    send_text(
        msg,
        mentioned_id,
        mentioned_mobile,
    )


def handle_warning_text(msg: str) -> str:
    """
    处理警告文本消息函数
    :param msg: 消息内容
    :return: 处理后的消息内容
    """
    msg += f"http://{IPv4}\n"
    msg += f"http://[{IPv6}]\n"
    msg += f"⏰{get_now_time()}"
    return msg


def send_process_except_warning_msg():
    """
    发送进程异常警告消息函数
    """
    warning_message = f"⚠️⚠️{SERVER_NAME}获取进程失败！⚠️⚠️\n"
    send_text(msg=handle_warning_text(warning_message), msg_type="warning")


def send_cpu_except_warning_msg(cpu_id: int):
    """
    发送CPU异常警告消息函数
    """
    warning_message = f"⚠️⚠️{SERVER_NAME}获取CPU:{cpu_id}温度失败！⚠️⚠️\n"
    send_text(msg=handle_warning_text(warning_message), msg_type="warning")


def send_cpu_temperature_warning_msg(cpu_id: int, cpu_temperature: float):
    """
    发送CPU温度异常警告消息函数
    """
    warning_message = f"🤒🤒{SERVER_NAME}的CPU:{cpu_id}温度已达{cpu_temperature}°C\n"
    send_text(msg=handle_warning_text(warning_message), msg_type="warning")
