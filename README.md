# NVI-Notify

NVIDIA GPU监控工具，支持常见的Webhook通知。

Auto monitor NVIDIA GPU auto sends a status message to webhook when GPU usage is changed.

## 支持的WebHook

- WeWork

## 环境要求

大部分代码仅支持Linux系统.

**经测试:**

CPU监控部分仅支持Linux系统.

## Usage

Please set environment variable GPU_MONITOR_WEBHOOK_WEWORK

```bash
export GPU_MONITOR_WEBHOOK_WEWORK="your webhook key"
```

## Run

```bash
pip install -r requirements.txt
python main.py
```

## 防火墙规则

```bash
sudo iptables -I INPUT -p tcp --dport 8080 -j ACCEPT

# 添加规则
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
sudo ip6tables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080

# 删除规则
# sudo iptables -t nat -D PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8080
```

## Systemd Service

### Install Service

```bash
sudo python systemd.py --install
```

### Uninstall Service

```bash
sudo python systemd.py --uninstall
```

## Log(Coming soon...)

The log file is located at ``.

If you want to view the log, you can use the following command:

```bash
sudo journalctl -u nvinotify
```

## Group-Center

### Update Plugin

```bash
pip install --upgrade li-group-center -i https://pypi.python.org/simple
```

## TODO

- [ ] Log System
- [ ] Message Center
- [ ] Support for Feishu

## 系列项目

### GPU看板(前端)

* 可以部署在中心服务器节点，也可以部署在本地节点。

* 推荐使用`npm run build`构建后使用`NGINX`进行部署。

https://github.com/a645162/web-gpu-dashboard

### GPU监控脚本(本项目)

https://github.com/a645162/nvi-notify

### 测试数据后端

https://github.com/a645162/backend-gpu-dashboard-test

## 思考中...

- [ ] Support for DingTalk
- [ ] Support for Bark
- [ ] Support for PushDeer
- [ ] Support for PushPlus

## References

https://github.com/XuehaiPan/nvitop/blob/main/README.md

## Thanks

[XuehaiPan/nvitop](https://github.com/XuehaiPan/nvitop)
