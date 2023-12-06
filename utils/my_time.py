from datetime import datetime


def get_now_time():
    # 获取当前时间
    current_time = datetime.now()
    # 将当前时间格式化为字符串
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    return formatted_time
