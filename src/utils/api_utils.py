from group_center.core.feature import custom_client_message

from src.api import data_manager
from src.config import settings
from src.entity import process
from src.utils import common_utils, logs

logger = logs.get_logger()
data_manager_ins = data_manager.get_data_manager()


def get_nvitop_result() -> str:
    _, result, _ = common_utils.get_terminal_output("nvitop -U")
    return result


def get_system_info_dict() -> dict:
    system_info: dict = {
        "memoryPhysicTotalMb": 4096,
        "memoryPhysicUsedMb": 2048,
        "memorySwapTotalMb": 4096,
        "memorySwapUsedMb": 2048,
    }

    system_info.update(data_manager_ins.system_info)

    return system_info


def get_gpu_count_backend() -> int:
    # For debug use
    current_gpu_task = data_manager_ins.gpu_task

    return len(current_gpu_task)


def get_gpu_usage_dict(gpu_index: int) -> dict:
    # all_gpu_info = data_manager_ins.gpu_info
    # all_gpu_usage = data_manager_ins.gpu_usage

    current_gpu_info = data_manager_ins.gpu_info[gpu_index]
    current_gpu_usage = data_manager_ins.gpu_usage[gpu_index]

    response_gpu_usage = {
        "result": len(data_manager_ins.gpu_usage),
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


def get_gpu_task_dict_list(gpu_index: int) -> list[dict]:
    current_gpu_processes: list[process.GPUProcessInfo] = data_manager_ins.gpu_task[
        gpu_index
    ]

    task_list = []

    for process_obj in current_gpu_processes:
        # 计算检测间隔（秒）
        detection_interval_seconds = int(
            settings.GPU_MONITOR_SAMPLING_INTERVAL * settings.MAX_CONSECUTIVE_ZERO_COUNT
        )

        task_list.append(
            {
                "id": process_obj.pid,
                "pid": process_obj.pid,
                "name": process_obj.user.name_cn,  # type: ignore
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
                "pythonVersion": process_obj.python_version,
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
                "zeroTotalGpuAlertCount": process_obj.total_gpu_idle_alert_count,
                "zeroTotalCpuAlertCount": process_obj.total_cpu_idle_alert_count,
                "zeroAlreadyAlertedGpuUsage": process_obj.had_cpu_idle_alert,
                "zeroAlreadyAlertedCpuUsage": process_obj.had_cpu_idle_alert,
                "zeroMaxConsecutiveCount": process_obj.max_idle_count,
                "zeroDetectionIntervalSeconds": detection_interval_seconds,
            }
        )

    return task_list


def get_disk_usage() -> list[dict]:
    mount_point_list: list[str] = [
        key for key in data_manager_ins.disk_info_response_dict
    ]
    mount_point_list.sort()

    dict_list: list[dict] = []

    for mount_point in mount_point_list:
        dict_list.append(data_manager_ins.disk_info_response_dict[mount_point])

    return dict_list


def get_disk_usage_user_dict_list() -> list[dict]:
    return []


def machine_user_message_backend(user_name: str, content: str) -> None:
    logger.info(f"[Machine User Message]userName: {user_name}, content: {content}")
    custom_client_message.machine_user_message_directly(user_name, content)
