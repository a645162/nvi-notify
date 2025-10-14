#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
程序重启脚本
用于在更新后重启主程序
"""

import os
import subprocess
import sys
import time
import signal


def restart_program(current_pid: int, python_executable: str, script_path: str, current_dir: str):
    """
    重启程序函数
    
    Args:
        current_pid: 当前进程PID
        python_executable: Python解释器路径
        script_path: 主程序脚本路径
        current_dir: 工作目录
    """
    print(f"当前进程PID: {current_pid}")
    
    # 等待一小段时间确保Flask响应已发送
    print("等待响应发送完成...")
    time.sleep(2)
    
    # 启动新进程
    print("启动新进程...")
    new_process = subprocess.Popen([python_executable, script_path], cwd=current_dir)
    print(f"新进程PID: {new_process.pid}")
    
    # 等待新进程完全启动
    print("等待新进程启动...")
    time.sleep(5)
    
    # 杀死旧进程
    print(f"正在杀死旧进程 {current_pid}")
    try:
        os.kill(current_pid, signal.SIGTERM)
        print("重启完成")
    except ProcessLookupError:
        print("进程已不存在")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("用法: python restart_program.py <current_pid> <python_executable> <script_path> <current_dir>")
        sys.exit(1)
    
    current_pid = int(sys.argv[1])
    python_executable = sys.argv[2]
    script_path = sys.argv[3]
    current_dir = sys.argv[4]
    
    restart_program(current_pid, python_executable, script_path, current_dir)