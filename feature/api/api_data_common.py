from typing import List

from group_center.core.feature.custom_client_message import (
    machine_user_message_directly,
)

from feature.group_center.data_manager import DataManager
from feature.utils.common_utils import do_command
from feature.utils.logs import get_logger

logger = get_logger()


def get_nvitop_result() -> str:
    _, result, _ = do_command("nvitop -U")
    return result


def get_system_info_dict() -> dict:
    system_info: dict = {
        "memoryPhysicTotalMb": 4096,
        "memoryPhysicUsedMb": 2048,
        "memorySwapTotalMb": 4096,
        "memorySwapUsedMb": 2048,
    }

    system_info.update(DataManager().system_info)

    return system_info


def get_gpu_count_backend() -> int:
    # For debug use
    current_gpu_task = DataManager().gpu_task

    return len(current_gpu_task)


def get_gpu_usage_dict(gpu_index: int) -> dict:
    # all_gpu_info = DataManager().gpu_info
    # all_gpu_usage = DataManager().gpu_usage

    current_gpu_info = DataManager().gpu_info[gpu_index]
    current_gpu_usage = DataManager().gpu_usage[gpu_index]

    response_gpu_usage = {
        "result": len(DataManager().gpu_usage),
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

    current_gpu_processes: list[GPUProcessInfo] = DataManager().gpu_task[gpu_index]

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
                "topPythonPid": process_obj.top_python_pid,
                "condaEnv": process_obj.conda_env,
                "screenSessionName": process_obj.screen_session_name,
                "pythonVersion": process_obj.python_version,
                "command": process_obj.command,
                "taskMainMemoryMB": int(process_obj.task_main_memory_mb),
                "cudaRoot": str(process_obj.cuda_root),
                "cudaVersion": str(process_obj.cuda_version),
                "cudaVisibleDevices": str(process_obj.cuda_visible_devices),
                "driverVersion": str(process_obj.nvidia_driver_version),
                "userEnvEpoch": str(process_obj.group_center_user_realtime_str),
            }
        )

    return task_list


def get_disk_usage_dict_list() -> List[dict]:
    mount_point_list: List[str] = [
        key for key in DataManager().disk_info_response_dict.keys()
    ]
    mount_point_list.sort()

    dict_list: List[dict] = []

    for mount_point in mount_point_list:
        dict_list.append(DataManager().disk_info_response_dict[mount_point])

    return dict_list


def get_disk_usage_user_dict_list() -> List[dict]:
    return []


def machine_user_message_backend(user_name: str, content: str):
    logger.info(f"[Machine User Message]userName: {user_name}, content: {content}")
    machine_user_message_directly(user_name=user_name, content=content)
