# 如何在 Linux 下快速定位「root 运行的 Python 进程」及其可执行文件

在排查 Flask、Django 或其他 Python 服务端口占用或异常行为时，通常需要两步：  
1. **找出所有由 root 用户启动的 Python 进程**；  
2. **获得这些进程的可执行文件全路径**。

下面把两条链路合并成一份简洁、可复制的操作手册，涵盖常用发行版（Ubuntu / CentOS / Debian）。

---

## 1. 一步列出 root 的 Python 进程

| 工具 | 命令 | 说明 |
|---|---|---|
| **`pgrep`**（推荐） | `sudo pgrep -au root '[p]ython'` | 一行输出 PID + 完整命令行，无 grep 自匹配 |
| **`ps`** | `sudo ps -u root -f | grep -i '[p]ython'` | 传统组合，字段更全 |
| **`ps`** 进阶 | `sudo ps -eo pid,user,cmd | awk '$2=="root" && /[p]ython/'` | 方便二次编程处理 |

示例输出（`pgrep`）：
```
1234 /usr/bin/python3 /opt/myapp/main.py
5678 /opt/venv/bin/python /opt/venv/bin/gunicorn -w 4 app:app
```

---

## 2. 从 PID 反查可执行文件路径

拿到 PID 后，两条命令即可：

```bash
# 精确获得可执行文件绝对路径
sudo readlink -f /proc/<PID>/exe

# 若想同时看工作目录
sudo pwdx <PID>
```

快速一次性脚本（复制即用）：

```bash
#!/bin/bash
# list_root_python.sh
for pid in $(pgrep -u root -f '[p]ython'); do
    exe=$(readlink -f /proc/$pid/exe)
    cwd=$(pwdx $pid | awk '{print $2}')
    printf "%-6s %-40s %s\n" "$pid" "$exe" "$cwd"
done
```

运行示例：
```
$ ./list_root_python.sh
1234   /usr/bin/python3.11                      /opt/myapp
5678   /opt/venv/bin/python3.10                 /opt/venv
```

---

## 3. 场景速查表

| 场景 | 一键命令 |
|---|---|
| 查看 root 的所有 Python 进程 | `sudo pgrep -au root '[p]ython'` |
| 查 PID 1234 的绝对路径 | `sudo readlink -f /proc/1234/exe` |
| 查 PID 1234 当前工作目录 | `sudo pwdx 1234` |
| 查哪个 Python 监听了 8000 端口 | `sudo lsof -i :8000 -a -c python` |

---

## 4. 小结

- **最快定位**：`pgrep -au root '[p]ython'`  
- **拿到 PID 后**：`/proc/<PID>/exe` 和 `pwdx` 足够解决 99 % 的问题。  
- 以上命令均无需安装额外软件，适用于任何 Linux 发行版。
