import subprocess
from typing import List

from feature.global_variable.gpu import (
    global_gpu_info,
    global_gpu_task,
    global_gpu_usage,
)
from feature.global_variable.system import global_system_info

from group_center.core.feature.machine_user_message \
    import machine_user_message_directly

from feature.utils.logs import get_logger

logger = get_logger()


def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout
    except Exception as e:
        return str(e), 500


def get_nvitop_result() -> str:
    return run_command("nvitop -U")


def get_system_info_dict() -> dict:
    system_info: dict = {
        "memoryPhysicTotalMb": 4096,
        "memoryPhysicUsedMb": 2048,
        "memorySwapTotalMb": 4096,
        "memorySwapUsedMb": 2048,
    }

    system_info.update(global_system_info)

    return system_info


def get_gpu_count() -> int:
    return len(global_gpu_task)


def get_gpu_usage_dict(gpu_index: int) -> dict:
    # all_gpu_info = global_gpu_info
    # all_gpu_usage = global_gpu_usage

    current_gpu_info = global_gpu_info[gpu_index]
    current_gpu_usage = global_gpu_usage[gpu_index]

    response_gpu_usage = {
        "result": len(global_gpu_usage),
        "gpuName": "Test GPU",
        "coreUsage": "0",
        "memoryUsage": "0",
        "gpuMemoryUsage": "0GiB",
        "gpuMemoryTotal": "0GiB",
        "gpuPowerUsage": "0",
        "gpuTDP": "0",
        "gpuTemperature": "0",
    }

    response_gpu_usage.update(current_gpu_info)
    response_gpu_usage.update(current_gpu_usage)

    return response_gpu_usage


def get_gpu_task_dict_list(gpu_index: int) -> List[dict]:
    from feature.monitor.gpu.gpu_process import GPUProcessInfo

    current_gpu_processes: list[GPUProcessInfo] = global_gpu_task[gpu_index]

    task_list = []

    for process_obj in current_gpu_processes:
        task_list.append(
            {
                "id": process_obj.pid,
                "name": process_obj.user.name_cn,
                "debugMode": process_obj.is_debug,
                "projectDirectory": process_obj.cwd,
                "projectName": process_obj.project_name,
                "pyFileName": process_obj.python_file,
                "runTime": process_obj.running_time_human,
                "startTimestamp": int(process_obj.start_time) * 1000,
                "gpuMemoryUsage": int(process_obj.task_gpu_memory >> 10 >> 10),
                "gpuMemoryUsageMax": int(process_obj.task_gpu_memory_max >> 10 >> 10),
                "worldSize": process_obj.world_size,
                "localRank": process_obj.local_rank,
                "condaEnv": process_obj.conda_env,
                "screenSessionName": process_obj.screen_session_name,
                "pythonVersion": process_obj.python_version,
                "command": process_obj.command,
                "taskMainMemoryMB": int(process_obj.task_main_memory_mb),
                "cudaRoot": str(process_obj.cuda_root),
                "cudaVersion": str(process_obj.cuda_version),
                "cudaVisibleDevices": str(process_obj.cuda_visible_devices),
                "driverVersion": str(process_obj.nvidia_driver_version),
            }
        )

    return task_list


def machine_user_message_backend(user_name: str, content: str):
    logger.info(f"[Machine User Message]userName: {user_name}, content: {content}")
    machine_user_message_directly(
        user_name=user_name,
        content=content
    )
