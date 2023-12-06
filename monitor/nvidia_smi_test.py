import nvidia_smi

def get_gpu_info():
    try:
        nvidia_smi.nvmlInit()
        device_count = nvidia_smi.nvmlDeviceGetCount()
        gpu_info = []
        for i in range(device_count):
            handle = nvidia_smi.nvmlDeviceGetHandleByIndex(i)
            gpu_name = nvidia_smi.nvmlDeviceGetName(handle).decode()
            utilization = nvidia_smi.nvmlDeviceGetUtilizationRates(handle)
            gpu_utilization = utilization.gpu
            gpu_info.append({'name': gpu_name, 'utilization': gpu_utilization})
        nvidia_smi.nvmlShutdown()
        return gpu_info
    except Exception as e:
        return str(e)

gpu_info = get_gpu_info()
for gpu in gpu_info:
    print(f"GPU Name: {gpu['name']}, Utilization: {gpu['utilization']}%")