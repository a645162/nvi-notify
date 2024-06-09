from feature.monitor.info.gpu_info import GPUInfo


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

    multiDeviceLocalRank: int = 0
    multiDeviceWorldSize: int = 0

    cudaRoot: str = ""
    cudaVersion: str = ""

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
        from feature.monitor.GPU.gpu_process import GPUProcessInfo

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

        all_tasks_msg: str = "".join(gpu_process_obj.gpu_all_tasks_msg_dict.values())
        self.allTaskMessage = all_tasks_msg

        # GPU 信息
        gpu_status: GPUInfo = gpu_process_obj.gpu_status
        self.gpuUsagePercent = gpu_status.utl
        self.gpuMemoryUsageString = self.__fix_data_size_str(gpu_status.mem_usage)
        self.gpuMemoryFreeString = self.__fix_data_size_str(gpu_status.mem_free)
        self.gpuMemoryTotalString = self.__fix_data_size_str(gpu_status.mem_total)
        self.gpuMemoryPercent = gpu_status.mem_percent

        self.taskGpuId = gpu_process_obj.gpu_id
        self.taskGpuName = gpu_process_obj.gpu_name

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
        self.multiDeviceLocalRank = gpu_process_obj.local_rank
        self.multiDeviceWorldSize = gpu_process_obj.world_size

        # CUDA 信息
        self.cudaRoot = gpu_process_obj.cuda_root
        self.cudaVersion = gpu_process_obj.cuda_version

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
