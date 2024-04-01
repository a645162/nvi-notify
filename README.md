# NVIDIA-SMI WebHook Notify

NVIDIA显卡监控工具，支持Webhook通知。

Auto monitor NVIDIA GPU auto sends a status message to webhook when GPU usage is changed.

## 支持的WebHook

- WeWork

## 环境要求

大部分代码仅支持Linux系统.

经测试:
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

## TODO

- [ ] Log System
- [ ] Support for Feishu

## 思考中...

- [ ] Support for DingTalk
- [ ] Support for Bark
- [ ] Support for PushDeer
- [ ] Support for PushPlus

## References

https://github.com/XuehaiPan/nvitop/blob/main/README.md

## Thanks

[XuehaiPan/nvitop](https://github.com/XuehaiPan/nvitop)
