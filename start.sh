#!/bin/bash

# Enable the option to exit immediately if any command exits with a non-zero status
set -e

env
file_path="$HOME/.env/gpu_monitor.sh"

if [ -e "$file_path" ]; then
    echo "ENV File exists. Sourcing it..."
    # shellcheck disable=SC1090
    source "$file_path"
else
    echo "ENV File does not exist."
    echo "Skipping sourcing ENV file..."
fi

# Load Functions
source "scripts/env.sh"

check_and_load_env_variable "SERVER_NAME" ""

# Deploy webhook
check_and_load_env_variable "GPU_MONITOR_WEBHOOK_WEWORK_DEPLOY" ""

# Test webhook(Only for test)
check_and_load_env_variable "GPU_MONITOR_WEBHOOK_WEWORK_TEST" ""

check_and_load_env_variable "GPU_MONITOR_SLEEP_TIME_START" ""
check_and_load_env_variable "GPU_MONITOR_SLEEP_TIME_END" ""
check_and_load_env_variable "DELAY_SEND_SECONDS" ""

check_and_load_env_variable "GPU_MONITOR_WEBHOOK_WEWORK_DEPLOY" ""

export GPU_MONITOR_WEBHOOK_WEWORK="$GPU_MONITOR_WEBHOOK_WEWORK_DEPLOY"
export GPU_MONITOR_WEBHOOK_WEWORK_WARNING="$GPU_MONITOR_WEBHOOK_WEWORK_TEST"

echo "Python path:"
which python

echo "Python version:"
python --version

python main.py
