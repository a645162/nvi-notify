# Update API 使用说明

## 接口信息

- **URL**: `/update`
- **方法**: `POST`
- **功能**: 自动更新程序并重启

## 接口描述

该接口用于自动更新程序，具体功能包括：

1. 检查当前目录是否为Git项目（检查`.git`目录是否存在）
2. 执行`git pull`命令拉取最新代码
3. 如果拉取成功，自动重启当前程序

## 使用示例

### 使用curl测试

```bash
curl -X POST http://localhost:8080/update
```

### 使用Python requests测试

```python
import requests

response = requests.post('http://localhost:8080/update')
print(response.json())
```

## 响应格式

### 成功响应

```json
{
  "success": true,
  "message": "Update successful, program is restarting",
  "current_pid": 12345,
  "git_output": "git pull output content"
}
```

### 失败响应

#### 非Git项目

```json
{
  "success": false,
  "message": "Current directory is not a Git project, cannot perform update"
}
```

#### git pull失败

```json
{
  "success": false,
  "message": "git pull failed: error message"
}
```

#### 其他错误

```json
{
  "success": false,
  "message": "Error during update process: error message"
}
```

## 重启机制

更新接口的重启流程如下：

1. **先返回响应**: 确保HTTP响应已发送给客户端
2. **调用重启脚本**: 启动独立的Python重启脚本 [`restart_program.py`](restart_program.py)
3. **延迟重启**: 等待2秒确保响应完全发送
4. **更新依赖包**: 执行以下pip安装命令：
   - `pip install -U "li-group-center>=2.5.0" -i https://pypi.python.org/simple`
   - `pip install -U -r requirements.txt`
5. **启动新进程**: 使用相同的Python解释器启动新的程序实例
6. **等待启动**: 等待5秒确保新进程完全启动
7. **杀死旧进程**: 使用SIGTERM信号终止当前进程

重启脚本 [`restart_program.py`](restart_program.py) 是一个独立的Python脚本，接收以下参数：
- `current_pid`: 当前进程PID
- `python_executable`: Python解释器路径
- `script_path`: 主程序脚本路径
- `current_dir`: 工作目录

## 注意事项

1. **Git状态**: 接口执行前需要确保没有未提交的更改，否则git pull可能会失败
2. **权限**: 确保程序有执行git命令和重启的权限
3. **重启机制**: 重启是通过启动新进程并杀死旧进程实现的
4. **日志**: 所有操作都会记录在程序日志中
5. **响应保证**: 重启操作在HTTP响应返回后才开始，确保客户端收到响应

## 安全考虑

- 该接口应该在生产环境中谨慎使用
- 建议添加认证机制或限制访问IP
- 确保只有授权用户能够触发更新操作
