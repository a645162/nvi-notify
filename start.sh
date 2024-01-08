#!/bin/bash

export GPU_MONITOR_LOCAL_IP=$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1')
export GPU_MONITOR_WEBHOOK_WEWORK=""
export GPU_MONITOR_SLEEP_TIME_START="23:00"
export GPU_MONITOR_SLEEP_TIME_END="7:30"

python main.py
