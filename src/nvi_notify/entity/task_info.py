from __future__ import annotations

from typing import TYPE_CHECKING

from nvi_notify.config import settings, user_info
from nvi_notify.monitor import enums

if TYPE_CHECKING:
    from nvi_notify.entity import gpu, process


class TaskInfoForRemote:
    taskId: str = ""

    messageType = ""

    taskType = ""
    taskStatus = ""
    taskUser = ""

    taskPid = 0
    taskMainMemory = 0

    allTaskMessage: str = ""

    # GPU
    gpuUsagePercent: float = 0.0
    gpuMemoryUsageString: str = ""
    gpuMemoryFreeString: str = ""
    gpuMemoryTotalString: str = ""
    gpuMemoryPercent: float = 0.0

    taskGpuId = 0
    taskGpuName = ""

    #    taskGpuMemoryMb = 0
    taskGpuMemoryGb = 0.0
    taskGpuMemoryHuman = ""

    #    taskGpuMemoryMaxMb = 0
    taskGpuMemoryMaxGb = 0.0

    isMultiGpu: bool = False
    multiDeviceLocalRank: int = 0
    multiDeviceWorldSize: int = 0
    topPythonPid: int = -1

    cudaRoot: str = ""
    cudaVersion: str = ""

    isDebugMode: bool = False

    taskStartTime: int = 0
    taskFinishTime: int = 0
    taskRunningTimeString: str = ""
    taskRunningTimeInSeconds = 0

    projectDirectory: str = ""
    projectName: str = ""
    screenSessionName: str = ""
    pyFileName: str = ""

    pythonVersion: str = ""
    commandLine: str = ""
    condaEnvName: str = ""

    def __init__(self, gpu_process_obj: process.GPUProcessInfo) -> None:
        self.update(gpu_process_obj=gpu_process_obj)

    @staticmethod
    def __fix_data_size_str(size_str: str) -> str:
        new_size_str = size_str

        while "GiB" in new_size_str:
            new_size_str = new_size_str.replace("GiB", "GB")

        while "MiB" in new_size_str:
            new_size_str = new_size_str.replace("MiB", "MB")

        while "KiB" in new_size_str:
            new_size_str = new_size_str.replace("KiB", "KB")

        return new_size_str

    def update(self, gpu_process_obj: process.GPUProcessInfo) -> None:
        # 任务唯一标识符
        self.taskId = gpu_process_obj.task_id

        # 任务类型
        self.taskType = "GPU"
        # 任务状态
        self.taskStatus = gpu_process_obj.state.value

        # 用户
        self.taskUser = gpu_process_obj.user.name_cn  # type: ignore

        # 进程信息
        self.taskPid = gpu_process_obj.pid
        self.taskMainMemory = gpu_process_obj.task_main_memory_mb

        # GPU 信息
        gpu: gpu.GPU = gpu_process_obj.gpu
        self.gpuUsagePercent = gpu.gpu_utilization
        self.gpuMemoryUsageString = self.__fix_data_size_str(gpu.memory_used_human)
        self.gpuMemoryFreeString = self.__fix_data_size_str(gpu.memory_free_human)
        self.gpuMemoryTotalString = self.__fix_data_size_str(gpu.memory_total_human)
        self.gpuMemoryPercent = gpu.memory_percent

        self.allTaskMessage = gpu.all_tasks_msg_body
        self.taskGpuId = gpu.gpu_id
        self.taskGpuName = gpu.name

        self.taskGpuMemoryGb = round(
            (gpu_process_obj.task_gpu_memory >> 10 >> 10) / 1024, 2
        )
        self.taskGpuMemoryHuman = self.__fix_data_size_str(
            gpu_process_obj.task_gpu_memory_human
        )
        self.taskGpuMemoryMaxGb = round(
            (gpu_process_obj.task_gpu_memory_max >> 10 >> 10) / 1024, 2
        )

        # 多卡
        self.isMultiGpu = gpu_process_obj.is_multi_gpu
        self.multiDeviceLocalRank = gpu_process_obj.local_rank
        self.multiDeviceWorldSize = gpu_process_obj.world_size
        self.topPythonPid = gpu_process_obj.top_python_pid

        # CUDA 信息
        self.cudaRoot = gpu_process_obj.cuda_root
        self.cudaVersion = gpu_process_obj.cuda_version

        self.isDebugMode = gpu_process_obj.is_debug

        # 运行时间
        self.taskStartTime = int(gpu_process_obj.start_time)
        self.taskFinishTime = int(gpu_process_obj.finish_time)
        self.taskRunningTimeString = gpu_process_obj.running_time_human
        self.taskRunningTimeInSeconds = gpu_process_obj.running_time_in_seconds

        # Name
        self.projectDirectory = gpu_process_obj.cwd.strip()
        self.projectName = gpu_process_obj.project_name.strip()
        self.screenSessionName = gpu_process_obj.screen_session_name.strip()
        self.pyFileName = gpu_process_obj.python_file.strip()

        self.pythonVersion = gpu_process_obj.python_version.strip()
        self.commandLine = gpu_process_obj.command.strip()
        self.condaEnvName = gpu_process_obj.conda_env.strip()


class TaskInfoForWebhook:
    def __init__(self, info: dict, task_event: enums.TaskEvent) -> None:
        self._task_event: enums.TaskEvent = task_event
        self._pid: int = info.get("pid", 0)
        self._gpu_id: int = info.get("gpu_id", 0)
        self._gpu_name: str = f"[GPU:{self._gpu_id}]" if settings.NUM_GPU > 1 else "GPU"
        self._gpu_status_msg: str = info.get("gpu_status_msg", "")

        self._user: user_info.UserInfo | None = info.get("user")

        self._running_time_human: str = info.get("running_time_human", "Unknown")
        self._task_gpu_memory_max_human: str = info.get(
            "task_gpu_memory_max_human", "0MiB"
        )

        self._is_debug: bool = info.get("is_debug", True)
        self._is_multi_gpu: bool = info.get("is_multi_gpu", False)
        self._world_size: int = info.get("world_size", 1)
        self._local_rank: int = info.get("local_rank", 0)

        self._screen_name: str = info.get("screen_session_name", "")
        self._project_name: str = info.get("project_name", "Unknown")
        self._python_file: str = info.get("python_file", "Unknown")

        self._num_task: int = info.get("num_task", 0)

    @property
    def pid(self) -> int:
        return self._pid

    @property
    def num_task(self) -> int:
        if self.task_event == enums.TaskEvent.CREATE:
            return self._num_task
        elif self.task_event == enums.TaskEvent.FINISH:
            return max(0, self._num_task - 1)

        return self._num_task

    @num_task.setter
    def num_task(self, value: int) -> None:
        self._num_task = value

    @property
    def task_event(self) -> enums.TaskEvent:
        return self._task_event

    @property
    def gpu_id(self) -> int:
        return self._gpu_id

    @property
    def gpu_name(self) -> str:
        return self._gpu_name

    @property
    def user(self) -> user_info.UserInfo | None:
        return self._user

    @property
    def running_time_human(self) -> str:
        return self._running_time_human

    @property
    def task_gpu_memory_max_human(self) -> str:
        return self._task_gpu_memory_max_human

    @property
    def is_debug(self) -> bool:
        return self._is_debug

    @property
    def is_multi_gpu(self) -> bool:
        return self._is_multi_gpu

    @property
    def local_rank(self) -> int:
        return self._local_rank

    @property
    def world_size(self) -> int:
        return self._world_size

    @property
    def multi_gpu_msg(self) -> str:
        if self.world_size > 1:
            if self.local_rank == 0:
                return f"{self.world_size}卡任务"
            return "-1"
        return ""

    @property
    def screen_name(self) -> str:
        return (
            f"[{self._screen_name}]"
            if len(self._screen_name) > 0
            else self._screen_name
        )

    @property
    def project_name(self) -> str:
        return self._project_name

    @property
    def python_file(self) -> str:
        return self._python_file

    @property
    def task_msg_body(self) -> str:
        if self.task_event == enums.TaskEvent.CREATE:
            return self.task_msg_body_for_create
        elif self.task_event == enums.TaskEvent.FINISH:
            return self.task_msg_body_for_finish
        else:
            return ""

    @property
    def task_msg_body_for_create(self) -> str:
        return (
            f"🚀{self.user.name_cn}的"  # type: ignore
            f"({self.screen_name}{self.project_name}-{self.python_file})启动"
            "\n"
        )

    @property
    def task_msg_body_for_finish(self) -> str:
        return (
            f"☑️{self.user.name_cn}的"  # type: ignore
            f"({self.screen_name}{self.project_name}-{self.python_file})完成，"
            f"用时{self.running_time_human}，"
            f"最大显存{self.task_gpu_memory_max_human}"
            "\n"
        )

    @staticmethod
    def get_emoji(key: int | str) -> str:
        EMOJI_DICT = {  # noqa: N806
            0: "0️⃣",
            1: "1️⃣",
            2: "2️⃣",
            3: "3️⃣",
            4: "4️⃣",
            5: "5️⃣",
            6: "6️⃣",
            7: "7️⃣",
            8: "8️⃣",
            9: "9️⃣",
            10: "🔟",
            "呲牙": "/::D",
        }
        if key not in EMOJI_DICT.keys():
            return "Unknown Emoji"
        return EMOJI_DICT[key]


class TaskInfoForSql:
    def __init__(self, info: dict, new_state: enums.TaskState | None = None) -> None:
        self.task_idx: str = info.get("task_id", "Unknown")
        self.pid: int = info.get("pid", 0)
        self.gpu_id: int = info.get("gpu_id", 0)

        self.user: str = info.get("user").name_cn  # type: ignore

        self.create_timestamp: int = round(info.get("start_time", 0.0))
        self.finish_timestamp: int = round(info.get("finish_time", 0.0))
        self.running_time_in_seconds: int = round(
            info.get("_running_time_in_seconds", 0.0)
        )
        self.gpu_mem_usage_max: str = info.get("task_gpu_memory_max_human", "0MiB")

        self.task_state: enums.TaskState = (
            new_state
            if new_state is not None
            else info.get("_state", enums.TaskState.NEWBORN)
        )

        self.is_debug: bool = info.get("is_debug", True)
        self.is_multi_gpu: bool = info.get("is_multi_gpu", False)
        self.conda_env: str = info.get("conda_env", "Unknown")

        self.screen_session_name: str = info.get("screen_session_name", "None")
        self.project_name: str = info.get("project_name", "Unknown")
        self.python_file: str = info.get("python_file", "Unknown")
