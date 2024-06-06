class GroupCenterGpuTaskInfo:
    serverName = ""
    serverNameEng = ""
    accessKey = ""

    taskID = 0

    messageType = ""

    taskType = ""
    taskStatus = ""
    taskUser = ""

    taskPid = 0
    taskMainMemory = 0

    taskGpuId = 0
    taskGpuName = ""

    #    taskGpuMemoryMb = 0
    taskGpuMemoryGb = 0.0
    taskGpuMemoryHuman = ""

    #    taskGpuMemoryMaxMb = 0
    taskGpuMemoryMaxGb = 0.0

    taskStartTime = 0.0

    taskRunningTimeString = ""
    taskRunningTimeInSeconds = 0

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

        # GPU 信息
        self.taskGpuId = gpu_process_obj.gpu_id
        self.taskGpuName = gpu_process_obj.gpu_name

        self.taskGpuMemoryGb = (gpu_process_obj.task_gpu_memory >> 10 >> 10) / 1024
        self.taskGpuMemoryHuman = gpu_process_obj.task_gpu_memory_human
        self.taskGpuMemoryMaxGb = (gpu_process_obj.task_gpu_memory_max >> 10 >> 10) / 1024

        # 运行时间
        self.taskStartTime = gpu_process_obj.start_time
        self.taskRunningTimeString = gpu_process_obj.running_time_human
        self.taskRunningTimeInSeconds = gpu_process_obj.running_time_in_seconds
