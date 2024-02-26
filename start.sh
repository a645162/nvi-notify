#!/bin/bash

# Enable the option to exit immediately if any command exits with a non-zero status
set -e

# env
env_file_path="$HOME/.env/gpu_monitor.sh"

if [ -e "$env_file_path" ]; then
    echo "ENV File exists. Sourcing it..."
    # shellcheck disable=SC1090
    source "$env_file_path"
else
    echo "ENV File does not exist."
    echo "Skipping sourcing ENV file..."
fi

# Load Functions
source "./scripts/env_func.sh"

# Check Env Variables
source "./config/check_env.sh"

export GPU_MONITOR_WEBHOOK_WEWORK="$GPU_MONITOR_WEBHOOK_WEWORK_DEPLOY"
export GPU_MONITOR_WEBHOOK_WEWORK_WARNING="$GPU_MONITOR_WEBHOOK_WEWORK_TEST"

echo "Python path:"
which python

echo "Python version:"
python --version

python main.py
