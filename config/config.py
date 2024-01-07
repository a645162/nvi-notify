from utils import env

gpu_monitor_usage_threshold = env.get_env_int("GPU_MONITOR_USAGE_THRESHOLD", 20)

gpu_monitor_sleep_time = env.get_env_int("GPU_MONITOR_SLEEP_TIME", 5)

web_server_host = '0.0.0.0'
web_server_port = 1234
