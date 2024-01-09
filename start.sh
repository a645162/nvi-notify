#!/bin/bash

export GPU_MONITOR_LOCAL_IP=$(ip -o -4 addr show | awk '$2 !~ /lo/ {print $4}' | grep -E '^10\.' | awk -F'/' '{print $1}')
export GPU_MONITOR_WEBHOOK_WEWORK=""
export GPU_MONITOR_WEBHOOK_WEWORK_WARNING=""
export SERVER_NAME="SERVER_NAME"
export GPU_MONITOR_SLEEP_TIME_START="23:00"
export GPU_MONITOR_SLEEP_TIME_END="7:30"

python main.py
