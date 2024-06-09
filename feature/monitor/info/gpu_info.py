class GPUInfo:
    def __init__(self, info: dict) -> None:
        self.utl: int = info.get("gpu_usage", 0)

        self.mem_percent: int = info.get("gpu_mem_percent", 0)
        self.mem_total_bytes: int = info.get("gpu_mem_total_bytes", 0)

        self.mem_total: str = info.get("gpu_mem_total", "0MiB")
        self.mem_usage: str = info.get("gpu_mem_usage", "0MiB")
        self.mem_free: str = info.get("gpu_mem_free", "0MiB")

        self.power_usage: int = info.get("gpu_power_usage", 0)
        self.temperature: int = info.get("gpu_temperature", 0)


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