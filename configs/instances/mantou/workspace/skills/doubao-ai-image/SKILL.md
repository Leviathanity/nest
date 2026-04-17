---
name: doubao-ai-image
description: |
  使用 AutoGLM 控制豆包 APP 生成 AI 图片 / Use AutoGLM to control Doubao app for AI image generation.
  通过 ADB 连接手机，运行智谱 AutoGLM 控制豆包 APP 生成图片，并保存发送到聊天窗口。
  Connect phone via ADB, run Zhipu AutoGLM to control Doubao app for image generation, save and send to chat.
---

> ⚠️ **建议使用子代理模式 + 较长超时**
> 
> 由于豆包生图需要打开 APP、输入提示词、等待生成、保存图片，**操作耗时较长**。
> 
> **必须使用子代理模式**，并设置超时时间：
> ```json
> {
>   "task": "使用豆包生成图片: 小孩子在浴缸游泳",
>   "timeoutSeconds": 300
> }
> ```
> 
> `timeoutSeconds: 300` (5分钟) 可以确保任务有足够时间完成。
>
> **完成后必须使用 message 工具发送图片给用户**：
> ```json
> {
>   "action": "send",
>   "filePath": "/path/to/image.png",
>   "message": "图片已生成，请查收！"
> }
> ```

# 技能：AutoGLM + 豆包 AI 图片生成

## 概述

使用 AutoGLM 控制豆包 APP 生成 AI 图片，并保存原图发送到聊天窗口。

## 适用场景

- 需要通过手机 AI APP 生成图片
- 将生成的图片发送到聊天工具

## 前置条件

1. **设备连接**：手机通过 ADB 连接到电脑（模拟器或真机）
2. **豆包 APP**：手机上已安装豆包
3. **AutoGLM**：已配置智谱 API Key
4. **ADB Keyboard**：手机上已安装并启用 ADB Keyboard

## 完整流程

### 步骤 1：连接设备并启动豆包

```bash
# 设备连接确认
adb devices

# 启动豆包 APP
adb shell am start -n com.larus.nova/com.larus.home.impl.MainActivity
```

### 步骤 2：使用 AutoGLM 生成图片

```bash
cd /home/node/Open-AutoGLM
/home/node/Open-AutoGLM/venv/bin/python main.py \
  --base-url https://open.bigmodel.cn/api/paas/v4 \
  --model "autoglm-phone" \
  --apikey "YOUR_API_KEY" \
  --device-id "host.docker.internal:5556" \
  --lang cn \
  "启动豆包，输入生成一张图片：小狗踢足球，发送，等待生成完成后点击图片查看大图，然后保存到相册"
```

### 步骤 3：查找最新保存的图片

豆包保存图片的路径：
- `/sdcard/nova_image/` - 主要路径
- `/sdcard/Android/data/com.larus.nova/files/images/sendimages/` - 次要路径

```bash
# 按时间排序查找最新图片
adb shell "ls -lt /sdcard/nova_image/ | head -5"
```

### 步骤 4：验证图片内容（可选）

使用视觉能力验证图片内容是否符合要求：

```python
from PIL import Image
# 或者使用 image 工具分析图片
```

### 步骤 5：拉取原图并发送

```bash
# 拉取最新图片
adb pull /sdcard/nova_image/[最新文件名].png /home/node/.openclaw/workspace/

# 发送到聊天
message action=send channel=feishu filePath=/home/node/.openclaw/workspace/xxx.png message="图片描述" target=用户ID
```

## 关键参数

| 参数 | 说明 |
|-----|-----|
| `device-id` | ADB 设备 ID，如 `host.docker.internal:5556` 或 `192.168.1.100:5555` |
| `apikey` | 智谱 API Key，可在 https://open.bigmodel.cn/ 获取 |
| `base-url` | 智谱 API 地址：`https://open.bigmodel.cn/api/paas/v4` |
| `model` | 模型名称：`autoglm-phone` |

## 常见问题

### Q1: 输入文字失败
- 确保 ADB Keyboard 已安装并启用
- 检查设备连接是否正常

### Q2: 找不到保存的图片
- 检查 `/sdcard/nova_image/` 目录
- 检查 `/sdcard/Android/data/com.larus.nova/files/images/sendimages/` 目录

### Q3: API Key 验证失败
- 检查 API Key 是否正确
- 确认 API Key 未过期

## 示例命令

```bash
# 完整示例
adb shell am start -n com.larus.nova/com.larus.home.impl.MainActivity
sleep 3

cd /home/node/Open-AutoGLM
/home/node/Open-AutoGLM/venv/bin/python main.py \
  --base-url https://open.bigmodel.cn/api/paas/v4 \
  --model "autoglm-phone" \
  --apikey "YOUR_API_KEY" \
  --device-id "host.docker.internal:5556" \
  --lang cn \
  "输入生成一张图片：小狗踢足球，发送，等待生成完成后保存"

# 查找并拉取最新图片
adb pull "$(adb shell "ls -t /sdcard/nova_image/ | head -1")" /home/node/.openclaw/workspace/latest.png
```

## 相关文件

- 技能目录：`/home/node/.openclaw/workspace/skills/`
- AutoGLM 目录：`/home/node/Open-AutoGLM/`
- 工作空间：`/home/node/.openclaw/workspace/`

## 更新日志

- 2026-02-21: 初始版本
