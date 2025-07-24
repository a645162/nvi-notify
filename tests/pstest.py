from pathlib import Path

import psutil

pid = 789527

process = psutil.Process(pid)
exe_path = Path(process.exe())
exe_name = exe_path.name

index = exe_name.find(".")
if index > -1:
    exe_name = exe_name[:index]
exe_name = exe_name.strip()

print(exe_name)
