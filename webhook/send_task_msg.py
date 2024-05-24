# -*- coding: utf-8 -*-

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
from utils.converter import get_human_str_from_byte
from utils.logs import get_logger
from webhook.wework import send_text

logger = get_logger()


def send_gpu_monitor_start_msg(gpu_id: int, all_process_info: Dict):
    """
    启动GPU监控函数
    :param gpu_id: GPU ID
    :param all_process_info: 所有进程信息字典
    """
    gpu_idx = f"[GPU:{gpu_id}]" if NUM_GPU > 1 else "GPU"

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
            f"{gpu_idx}监控启动\n"
            f"{get_emoji('呲牙') * len(all_process_info)}"
            f"{gpu_idx}上正在运行{len(all_process_info)}个任务：\n"
            f"{all_tasks_msg}\n"
            f"🌀{gpu_idx}核心占用: {gpu_status.utl}%\n"
            f"🌀{gpu_idx}显存占用: {gpu_status.mem_usage}/{gpu_status.mem_total} "
            f"({gpu_status.mem_percent}%)，{gpu_status.mem_free}空闲\n",
        )


def send_gpu_task_message(process_info: Dict, task_status: str):
    """
    发送GPU任务消息函数
    :param process_info: 进程信息字典
    :param task_status: 任务状态
    """
    gpu_name = f"[GPU:{process_info['gpu_id']}]" if NUM_GPU > 1 else "GPU"
    gpu_name_for_msg_header = gpu_name + "\n" if NUM_GPU > 1 else ""

    gpu_status = process_info.get("gpu_status")
    gpu_info_msg = (
        f"🌀{gpu_name}核心占用: {gpu_status.utl}%\n"
        f"🌀{gpu_name}显存占用: {gpu_status.mem_usage}/{gpu_status.mem_total} "
        f"({gpu_status.mem_percent}%)，{gpu_status.mem_free}空闲\n\n"
    )

    gpu_all_task_info_msg = f"{''.join(process_info['gpu_all_tasks_msg'].values())}"

    if not process_info["is_debug"]:
        # 工程名
        project_main_name = handle_project_main_name(
            project_name=process_info.get("project_name", ""),
            screen_name=process_info.get("screen_session_name", ""),
        )

        # Python文件名
        py_file = process_info.get("python_file", "")
        if py_file != "":
            py_file = str(py_file).strip()

            if len(py_file) > 0:
                py_file = "-" + py_file

        # 多卡
        multi_gpu_msg = ""
        if "is_multi_gpu" in process_info.keys() and process_info["is_multi_gpu"]:
            local_rank = int(process_info["local_rank"])
            world_size = int(process_info["world_size"])

            if world_size > 1:
                if local_rank == 0:
                    multi_gpu_msg = f"{world_size}卡任务"
                else:  # 非第一个使用的GPU不发送消息
                    return

        if task_status == "create":
            num_tasks = process_info["num_task"]
            emoji_num_task = get_emoji("呲牙") * (num_tasks)
            create_msg_header = (
                f"{gpu_name_for_msg_header}🚀"
                f"{process_info['user']['name']}的"
                f"{multi_gpu_msg}"
                f"({project_main_name}{py_file})启动"
                "\n"
            )
            gpu_task_status_info_msg = (
                f"{emoji_num_task}{gpu_name}上正在运行{num_tasks}个任务：\n"
            )
            handle_normal_text(
                msg=create_msg_header
                + gpu_info_msg
                + gpu_task_status_info_msg
                + gpu_all_task_info_msg
            )
        elif task_status == "finish":
            num_tasks = process_info["num_task"] - 1
            emoji_num_task = get_emoji("呲牙") * (num_tasks)
            finish_msg_header = (
                f"{gpu_name_for_msg_header}☑️"
                f"{process_info['user']['name']}的"
                f"{multi_gpu_msg}"
                f"({project_main_name}{py_file})完成，"
                f"用时{process_info['running_time_human']}，"
                f"最大显存{get_human_str_from_byte(process_info['task_gpu_memory_max'])}"
                "\n"
                "\n"
            )
            gpu_task_status_info_msg = (
                f"{emoji_num_task}{gpu_name}上正在运行{num_tasks}个任务：\n"
            )
            if num_tasks == 0:
                gpu_task_status_info_msg = f"{gpu_name}当前无任务\n"

            handle_normal_text(
                msg=finish_msg_header
                + gpu_info_msg
                + gpu_task_status_info_msg
                + gpu_all_task_info_msg,
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

    logfile_dir_path = Path("./log")
    if not os.path.exists(logfile_dir_path):
        os.makedirs(logfile_dir_path)

    with open(logfile_dir_path / "user_task.log", "a") as log_writer:
        if task_type == "create":
            output_log = (
                f"[GPU:{process_info['gpu_id']}]"
                f" {process_info['user']['name']} "
                f"create new {'debug ' if process_info['is_debug'] else ''}"
                f"task: {process_info['pid']}"
            )
        elif task_type == "finish":
            output_log = (
                f"[GPU:{process_info['gpu_id']}]"
                f" finish {process_info['user']['name']}'s {'debug ' if process_info['is_debug'] else ''}"
                f"task: {process_info['pid']}，用时{process_info['running_time_human']}"
            )
        log_writer.write(f"[{get_now_time()}]+{output_log} + \n")
        logger.info(output_log)
        print(output_log)


def handle_project_main_name(project_name: str = "", screen_name: str = "") -> str:
    project_name = project_name.strip()
    screen_name = screen_name.strip()

    if len(screen_name) == 0:
        if len(project_name) == 0:
            return "Unknown"

        return project_name

    return f"[{screen_name}]{project_name}"


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
        "normal",
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

def send_hard_disk_high_occupancy_warning_msg(
    name: str, mountpoint: str, total_GB: float, free_GB: float, percentage: float
):
    """
    发送硬盘高占用警告消息函数
    """
    hard_disk_name_for_msg = {"system": "系统盘", "data": "数据盘"}

    warning_message = (
        f"⚠️【硬盘可用空间不足】⚠️\n"
        f"{hard_disk_name_for_msg.get(name, 'Unknown')}(挂载点为{mountpoint})"
        f"剩余可用容量为{free_GB:.2f}GB，总容量为{total_GB:.2f}GB，占用率为{percentage:.2f}%\n"
    )

    handle_normal_text(msg=warning_message)
