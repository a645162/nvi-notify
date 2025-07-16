def is_multiprocessing_spawn(cmdline: list[str]) -> bool:
    """
    检查命令行是否为 multiprocessing 的 spawn 进程
    """
    if not cmdline:
        return False
    return any("--multiprocessing-fork" in cmd for cmd in cmdline)


if __name__ == "__main__":
    # 测试用例
    test_cli = """/home/konghaomin/.conda/envs/YOLOX/bin/python -c "from multiprocessing.spawn import spawn_main; spawn_main(tracker_fd=6, pipe_handle=36)" --multiprocessing-fork"""
    # 通常 cmdline 是一个 list，可以用 split 方式模拟
    test_cmdline = test_cli.split(" ")
    print("is_multiprocessing_spawn:", is_multiprocessing_spawn(test_cmdline))
