import datetime
from typing import List

from group_center.core.feature.custom_client_message import (
    machine_user_message_directly,
)

from config.settings import SERVER_NAME
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
    from config.settings import (
        GPU_MONITOR_SAMPLING_INTERVAL,
        MAX_CONSECUTIVE_ZERO_COUNT,
    )
    from feature.monitor.gpu.gpu_process import GPUProcessInfo

    current_gpu_processes: list[GPUProcessInfo] = DataManager().gpu_task[gpu_index]

    task_list = []

    for process_obj in current_gpu_processes:
        # 计算检测间隔（秒）
        detection_interval_seconds = int(
            GPU_MONITOR_SAMPLING_INTERVAL * MAX_CONSECUTIVE_ZERO_COUNT
        )

        task_list.append(
            {
                "id": process_obj.task_id,
                "pid": process_obj.pid,
                "name": process_obj.user.name_cn if process_obj.user else "",
                "debugMode": process_obj.is_debug,
                "projectDirectory": process_obj.cwd,
                "projectName": process_obj.project_name,
                "pyFileName": process_obj.python_file,
                "runTime": process_obj.running_time_human,
                "startTimestamp": int(process_obj.start_time) * 1000,
                "gpuMemoryUsage": int(process_obj.task_gpu_memory >> 10 >> 10),
                "gpuMemoryUsageMax": int(process_obj.task_gpu_memory_max >> 10 >> 10),
                "multiprocessingSpawn": process_obj.is_multiprocessing_spawn,
                "worldSize": process_obj.world_size,
                "localRank": process_obj.local_rank,
                "topPythonPid": process_obj.top_python_pid,
                "condaEnv": process_obj.conda_env,
                "screenSessionName": process_obj.screen_session_name,
                "pythonBinPath": process_obj.python_bin_path,
                "pythonVersion": process_obj.python_version,
                "torchVersion": process_obj.torch_version,
                "torchCudaVersion": process_obj.torch_cuda_version,
                "command": process_obj.command,
                "taskMainMemoryMB": int(process_obj.task_main_memory_mb),
                "cudaRoot": str(process_obj.cuda_root),
                "cudaVersion": str(process_obj.cuda_version),
                "cudaVisibleDevices": str(process_obj.cuda_visible_devices),
                "driverVersion": str(process_obj.nvidia_driver_version),
                "userEnvEpoch": str(process_obj.group_center_user_realtime_str),
                # 使用率
                "cpuPercent": round(process_obj.cpu_percent, 1),
                "gpuUtilization": round(process_obj.gpu_utilization, 1),
                # 零占用率监控相关字段
                "zeroTotalGpuAlertCount": process_obj.total_gpu_zero_alert_count,
                "zeroTotalCpuAlertCount": process_obj.total_cpu_zero_alert_count,
                "zeroAlreadyAlertedGpuUsage": process_obj.already_has_alerted_zero_gpu_usage,
                "zeroAlreadyAlertedCpuUsage": process_obj.already_has_alerted_zero_cpu_usage,
                "zeroMaxConsecutiveCount": process_obj.max_consecutive_zero_count,
                "zeroDetectionIntervalSeconds": detection_interval_seconds,
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
    content = content.strip()

    logger.info(f"[Machine User Message]userName: {user_name}, content: {content}")

    extra_list = []

    if SERVER_NAME and SERVER_NAME != "None":
        extra_list.append(f"From: {SERVER_NAME}")

    now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    extra_list.append(f"{now_time}")

    extra_str = "\n".join(extra_list)

    content = content + "\n\n" + extra_str

    machine_user_message_directly(user_name=user_name, content=content)
