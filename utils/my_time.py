from datetime import datetime, time


def get_now_time():
    # 获取当前时间
    current_time = datetime.now()
    # 将当前时间格式化为字符串
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    return formatted_time


def is_within_time_range(
        start_time=time(11, 0),
        end_time=time(7, 30)
):
    # 获取当前时间
    current_time = datetime.now().time()

    if start_time <= end_time:
        return start_time <= current_time <= end_time
    else:
        return start_time <= current_time or current_time <= end_time


if __name__ == '__main__':
    print(
        is_within_time_range(
            time(23, 00),
            time(7, 30)
        )
    )
