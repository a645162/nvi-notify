import psutil
import os

pid = 789527

process = psutil.Process(pid)
exe_path = process.exe()
exe_name = os.path.basename(exe_path)

index = exe_name.find(".")
if index > -1:
    exe_name=exe_name[:index]
exe_name=exe_name.strip()

print(exe_name)
