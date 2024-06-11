from feature.monitor.gpu.gpu import GPU


class TaskInfoForGroupCenter:
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

    cudaRoot: str = ""
    cudaVersion: str = ""

    isDebugMode: bool = False

    taskStartTime: int = 0
    taskFinishTime: int = 0
    taskRunningTimeString: str = ""
    taskRunningTimeInSeconds = 0

    projectName: str = ""
    screenSessionName: str = ""
    pyFileName: str = ""

    pythonVersion: str = ""
    commandLine: str = ""
    condaEnvName: str = ""

    def __init__(self, gpu_process_obj):
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

    def update(self, gpu_process_obj):
        from feature.monitor.gpu.gpu_process import GPUProcessInfo

        gpu_process_obj: GPUProcessInfo = gpu_process_obj

        # 任务唯一标识符
        self.taskId = gpu_process_obj.task_id

        # 任务类型
        self.taskType = "GPU"
        # 任务状态
        self.taskStatus = gpu_process_obj.state.value

        # 用户
        self.taskUser = gpu_process_obj.user.name_cn

        # 进程信息
        self.taskPid = gpu_process_obj.pid
        self.taskMainMemory = gpu_process_obj.task_main_memory_mb

        # GPU 信息
        gpu: GPU = gpu_process_obj.gpu
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
        self.projectName = gpu_process_obj.project_name
        self.screenSessionName = gpu_process_obj.screen_session_name
        self.pyFileName = gpu_process_obj.python_file

        self.pythonVersion = gpu_process_obj.python_version
        self.commandLine = gpu_process_obj.command
        self.condaEnvName = gpu_process_obj.conda_env
