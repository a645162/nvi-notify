# NVIDIA-SMI WebHook Notify

NVIDIA显卡监控工具，支持Webhook通知。

Auto monitor NVIDIA GPU auto sends a status message to webhook when GPU usage is changed.

## 支持的WebHook

- WeWork

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

## TODO

- [ ] Support for DingTalk
- [ ] Support for Bark
- [ ] Support for Feishu
- [ ] Support for PushDeer
- [ ] Support for PushPlus

## References

https://github.com/XuehaiPan/nvitop/blob/main/README.md

## Thanks

[XuehaiPan/nvitop](https://github.com/XuehaiPan/nvitop)