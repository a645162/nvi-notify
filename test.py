from nvitop import *
from config import keywords, config

nvidia_i = Device(0)
# print(str(int(float(nvidia_i.memory_total_human().split('GiB')[0]) * 1024))+'MiB',)
#       #f'{(nvidia_i.memory_total() / 1024 / 1024 / 1024):.2f}')


# all = nvidia_i.processes()
# for i, j in all.items():
#     process_name = j.name().lower()
#     if process_name in ['python']:
#         # print(process_name)
#         process_cmd_line = j.cmdline()
#         for line in process_cmd_line:
#             if line.split('/')[-1] == 'python' or line == 'python':
#                 process_cmd_line.remove(line)

#         if any(keyword in process_cmd_line[0] for keyword in ['vscode-server', 'debugpy']):
#             print(process_name, 'True')
#         else:
#             print(process_name, 'False')
#         print(j.cmdline())
def get_command_py_files(task_info: dict):
    cmdline = task_info["cmdline"]
    for cmd_str in cmdline:
        if cmd_str.lower().endswith(".py"):
            if "/" in cmd_str:
                cmd_list = cmd_str.split("/")
                print(cmd_list[-1])
                print(cmd_list[-1][:-3])

            #     return(f"{cmd_list[-2]}/{cmd_list[-1][:-3]}")
            else:
                return cmd_str[:-3]


gpu_task_info = {}
for pid, gpu_process in all.items():
      process_name = gpu_process.name().lower()

      if process_name == "python":
            # start_time = gpu_process.create_time()
            debug_flag = keywords.is_debug_process(gpu_process.cmdline())
            print(gpu_process.cwd()+'/')
            gpu_task_info[pid] = {
                "device": 0,
                "user": keywords.find_user_by_path(config.user_list, gpu_process.cwd()),
                "memory_usage": gpu_process.gpu_memory_human(),
                "command": gpu_process.command(),
                "cmdline": gpu_process.cmdline(),
                "running_time": gpu_process.running_time_human(),
                "debug": debug_flag,
            }
            print(gpu_process.cmdline())
            print(get_command_py_files(gpu_task_info[pid]))

# for idx, info in enumerate(gpu_task_info.values()):
#     all_tasks_msg = f"{'调试' if info['debug'] is not None else ''}"
#     all_tasks_msg += f"任务编号: {idx + 1}  "
#     all_tasks_msg += f"用户: {info['user']}  "
#     all_tasks_msg += f"显存占用: {info['memory_usage']}  "
#     all_tasks_msg += f"命令: {info['command']}  "
#     all_tasks_msg += f"运行时间: {info['running_time']}  "
#     all_tasks_msg += "\n"

# print(all_tasks_msg)
# print(gpu_task_info)

