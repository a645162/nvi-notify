#!/bin/bash

python_path=$(conda run -n nvitop which python)
if [ -z "$python_path" ]; then
    echo "Python not found in nvitop environment"
    exit 1
fi

echo "Python path: $python_path"

$python_path main.py
