class GroupCenterGpuTaskInfo:
    taskID: str = ""

    messageType = ""

    taskType = ""
    taskStatus = ""
    taskUser = ""

    taskPid = 0
    taskMainMemory = 0

    allTaskMessage: str = ""

    # GPU
    gpuUsagePercent: float = 0.0
    gpuMemoryUsage: str = ""
    gpuMemoryFree: str = ""
    gpuMemoryTotal: str = ""
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

    def update(self, gpu_process_obj):
        from monitor.GPU.gpu_process import GPUProcessInfo
        gpu_process_obj: GPUProcessInfo = gpu_process_obj

        # 任务唯一标识符
        self.taskID = gpu_process_obj.task_task_id

        # 任务类型
        self.taskType = "GPU"
        # 任务状态
        self.taskStatus = gpu_process_obj.state

        # 用户
        self.taskUser = gpu_process_obj.user_name

        # 进程信息
        self.taskPid = gpu_process_obj.pid
        self.taskMainMemory = gpu_process_obj.task_main_memory_mb

        all_tasks_msg: str = "".join(gpu_process_obj.gpu_all_tasks_msg.values())
        all_tasks_msg = str(all_tasks_msg).strip()
        self.allTaskMessage = all_tasks_msg

        # GPU 信息
        gpu_status = gpu_process_obj.gpu_status
        self.gpuUsagePercent = gpu_status.get("utl", 0.0)
        self.gpuMemoryUsage = gpu_status.get("mem_usage", "")
        self.gpuMemoryFree = gpu_status.get("mem_free", "")
        self.gpuMemoryTotal = gpu_status.get("mem_total", "")
        self.gpuMemoryPercent = gpu_status.get("mem_percent", 0.0)

        self.taskGpuId = gpu_process_obj.gpu_id
        self.taskGpuName = gpu_process_obj.gpu_name

        self.taskGpuMemoryGb = (gpu_process_obj.task_gpu_memory >> 10 >> 10) / 1024
        self.taskGpuMemoryHuman = gpu_process_obj.task_gpu_memory_human
        self.taskGpuMemoryMaxGb = (gpu_process_obj.task_gpu_memory_max >> 10 >> 10) / 1024

        # 多卡
        self.multiDeviceLocalRank = gpu_process_obj.local_rank
        self.multiDeviceWorldSize = gpu_process_obj.world_size

        # CUDA 信息
        self.cudaRoot = gpu_process_obj.cuda_root
        self.cudaVersion = gpu_process_obj.cuda_version

        # 运行时间
        self.taskStartTime = int(gpu_process_obj.start_time)
        self.taskRunningTimeString = gpu_process_obj.running_time_human
        self.taskRunningTimeInSeconds = gpu_process_obj.running_time_in_seconds

        # Name
        self.projectName = gpu_process_obj.project_name
        self.screenSessionName = gpu_process_obj.screen_session_name
        self.pyFileName = gpu_process_obj.python_file

        self.pythonVersion = gpu_process_obj.python_version
        self.commandLine = gpu_process_obj.command
        self.condaEnvName = gpu_process_obj.conda_env
