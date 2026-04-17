---
name: minimax-tts-video
description: |
  将 MiniMax TTS 语音合成与视频合并，通过微信发送语音消息
  解决微信无法直接发送语音条的问题
---

# MiniMax TTS 语音视频合成技能

## 概述

通过将 TTS 生成的语音与视频合并，实现微信语音消息的直接播放（无需下载文件）。

## 工作流程

1. 🎙️ MiniMax TTS 生成语音 → MP3
2. 🎬 ffmpeg 合并语音到视频 → MP4
3. 📱 微信直接播放视频即可听到语音

## 使用方式

### 基本用法

```bash
cd ~/.openclaw/workspace/skills/minimax-tts-video/scripts
./tts-video.sh "要说的文本" [输出文件路径]
```

### 参数说明

| 参数 | 必填 | 说明 |
|-----|-----|-----|
| text | ✅ | 要转换的文本 |
| output | ❌ | 输出 MP4 路径，默认 `/tmp/tts_video.mp4` |

### 可选环境变量

| 变量 | 默认值 | 说明 |
|-----|-------|-----|
| `TTS_MODEL` | `speech-2.8-hd` | TTS 模型 |
| `TTS_VOICE` | `male-qn-qingse` | 声音 ID |
| `VIDEO_DURATION` | 自动匹配语音时长 | 视频持续时间 |

## 示例

```bash
# 基本用法
./tts-video.sh "你好，欢迎使用语音合成功能"

# 指定输出路径
./tts-video.sh "这是一条测试消息" "/tmp/my_voice_video.mp4"
```

## 技术细节

### 微信语音限制

- 微信原生语音需要 SILK 编码格式，OpenClaw 暂不支持
- 视频方式可绕过限制，直接在微信中播放语音

### ffmpeg 命令

```bash
# 1. 生成纯色测试视频（时长匹配语音）
ffmpeg -f lavfi -i "color=c=blue:s=320x240:d=${DURATION}" \
       -i /tmp/tts_audio.mp3 \
       -c:v libx264 -c:a aac -shortest \
       /tmp/tts_video.mp4 -y

# 2. 提取并验证音频
ffprobe -v error -show_entries stream=codec_type,duration \
         -of default=noprint_wrappers=1 /tmp/tts_video.mp4
```

### 音频检测

```bash
ffmpeg -i output.mp4 -af "volumedetect" -f null /dev/null 2>&1 | grep -E "mean_volume|max_volume"
```

正常值：mean_volume ≈ -22dB, max_volume ≈ -7dB

## 依赖

- `minimax-tts` 技能（`~/.openclaw/workspace/skills/minimax-tts/`）
- `ffmpeg`（系统安装）
- `graiax-silkcoder`（Python 包，用于 SILK 格式处理）

## 文件结构

```
minimax-tts-video/
├── SKILL.md          # 本文档
└── scripts/
    └── tts-video.sh  # 主脚本
```

## 注意事项

1. 视频时长会自动匹配语音长度
2. 生成的视频为 320x240 分辨率，蓝色背景
3. 音频码率 128kbps AAC 格式
4. 微信中直接点击播放即可，无需下载
