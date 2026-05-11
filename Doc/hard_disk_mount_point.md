# 硬盘监控挂载点配置说明

## 配置格式

在 `.env.secure` 文件中使用 `HARD_DISK_MOUNT_POINT` 配置要监控的挂载点。

支持多种配置格式：

- 单个挂载点：`"/"`
- 多个挂载点：`"/, /mnt/hdd1"`
- 包含 home：`"/home, /mnt/hdd1"`

## 配置逻辑（monitor.py 第429-459行）

```python
# 解析配置的挂载点（支持 "/, /mnt/hdd1" 格式）
if isinstance(HARD_DISK_MOUNT_POINT, str):
    configured_mount_points = set(
        mp.strip() for mp in HARD_DISK_MOUNT_POINT.split(",") if mp.strip()
    )
else:
    configured_mount_points = set(HARD_DISK_MOUNT_POINT) if HARD_DISK_MOUNT_POINT else set()

# 添加 /home 到监控列表（如果配置中有）
if "/home" in configured_mount_points:
    mount_points_to_monitor.add("/home")

# 添加 / 到监控列表（如果配置中有且没有 /home）
if "/" in configured_mount_points and "/home" not in mount_points_to_monitor:
    mount_points_to_monitor.add("/")

# 添加其他配置的挂载点（如 /mnt/hdd1）
for mp in configured_mount_points:
    if mp != "/" and mp != "/home":
        mount_points_to_monitor.add(mp)
```

## 处理规则

| 配置 | 监控结果 |
|------|----------|
| `"/"` | `{"/"}` |
| `"/mnt/hdd1"` | `{"/mnt/hdd1"}` |
| `"/, /mnt/hdd1"` | `{"/", "/mnt/hdd1"}` |
| `"/home"` | `{"/home"}` |
| `"/home, /mnt/hdd1"` | `{"/home", "/mnt/hdd1"}` |

## 优先级说明

1. **/home 优先**：如果配置中有 `/home`，只监控 `/home`，不监控 `/`（因为 `/home` 是 `/` 的子目录）
2. **/ 其次**：如果配置中没有 `/home`，但有 `/`，则监控 `/`
3. **其他挂载点**：所有其他指定的挂载点都会被添加（如 `/mnt/hdd1`）

## 示例

假设 `.env.secure` 配置为：
```
HARD_DISK_MOUNT_POINT = "/, /mnt/hdd1"
```

解析过程：
1. 字符串分割：`["/", "/mnt/hdd1"]`
2. 去除空格：`{"/", "/mnt/hdd1"}`
3. `/home` 不在配置中，跳过
4. `/` 在配置中且没有 `/home`，添加 `/`
5. `/mnt/hdd1` 既不是 `/` 也不是 `/home`，添加 `/mnt/hdd1`

最终监控：`{"/", "/mnt/hdd1"}`
