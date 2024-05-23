from typing import Dict


class GPU_INFO:
    def __init__(self, info: Dict) -> None:
        self.utl: int = info.get("gpu_usage", 0)

        self.mem_percent: int = info.get("gpu_mem_percent", 0)
        self.mem_total_bytes: int = info.get("gpu_mem_total_bytes", 0)

        self.mem_total: str = info.get("gpu_mem_total", "0MiB")
        self.mem_usage: str = info.get("gpu_mem_usage", "0MiB")
        self.mem_free: str = info.get("gpu_mem_free", "0MiB")

        self.power_usage: int = info.get("gpu_power_usage", 0)
        self.temperature: int = info.get("gpu_temperature", 0)


class TASK_INFO_FOR_SQL:
    def __init__(self, info: Dict, new_state=None) -> None:
        self.task_idx: str = info.get("task_task_id", "Unknown")
        self.pid: int = info.get("pid", 0)
        self.gpu_id: int = info.get("gpu_id", 0)

        user_dict = info.get("user", {})
        if user_dict:
            self.user = user_dict.get("name", "Unknown")

        self.create_timestamp = round(info.get("start_time", 0.))

        try:
            self.finish_timestamp = round(info.get("finish_time", 0.))
        except:  # noqa: E722
            self.finish_timestamp = 0

        self.running_time_in_seconds = round(info.get("_running_time_in_seconds", 0.))
        self.gpu_mem_usage_max: str = info.get("task_gpu_memory_max_human", "0MiB")

        if new_state is None:
            if info.get("_state"):
                self.task_state = info.get("_state")
            else:
                self.task_state = "newborn"
        else:
            self.task_state: str = new_state

        self.is_debug: bool = info.get("is_debug", True)
        self.is_multi_gpu: bool = info.get("is_multi_gpu", False)
        self.conda_env: str = info.get("conda_env", "Unknown")

        self.screen_session_name: str = info.get("screen_session_name", "None")
        self.project_name: str = info.get("project_name", "Unknown")
        self.python_file: str = info.get("python_file", "Unknown")


def gpu_name_filter(gpu_name: str) -> str:
    current_str = gpu_name
    current_str_upper = gpu_name.upper()
    keywords = [
        "NVIDIA",
        "GeForce",
        "Quadro",
    ]

    # 遍历关键词列表
    for keyword in keywords:
        keyword_upper = keyword.upper()
        # 循环寻找大写字符串中的关键词
        while keyword_upper in current_str_upper:
            # 找到关键词在大写字符串中的位置
            index = current_str_upper.index(keyword_upper)
            # 计算关键词在原始字符串中的起始位置
            index_original = current_str_upper[:index].count(" ") - current_str[
                :index
            ].count(" ")
            # 删除原始字符串中的关键词
            current_str = (
                current_str[:index_original]
                + current_str[index_original + len(keyword) + 1 :]
            )
            # 更新大写字符串
            current_str_upper = current_str.upper()

    return current_str.strip()


