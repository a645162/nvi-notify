#!/usr/bin/env bash

conda activate nvitop

git pull

pip install -U "li-group-center>=2.5.1" -i https://pypi.python.org/simple

pip install -r requirements.txt
