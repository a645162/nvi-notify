# NVIDIA-SMI WebHook Notify

Auto monitor NVIDIA GPU auto sends a status message to webhook when GPU usage is changed.

## Support Webhook

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
