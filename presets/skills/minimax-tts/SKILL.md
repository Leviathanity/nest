---
name: minimax-tts
description: |
  使用 MiniMax Speech 2.6 API 进行语音合成 (TTS)
  将文本转换为语音并保存为音频文件。
---

# MiniMax 语音合成技能

## ⚠️ 重要提示

**语音合成 API 需要 Token Plan 专属 API Key**

根据 MiniMax 文档：
> 此 API Key 为 Token Plan 专属，和按量计费 API Key 并不互通。

如果您当前的 API Key 显示 "token plan not support model" 错误，请：
1. 访问 [接口密钥页面](https://platform.minimaxi.com/user-center/basic-information/interface-key)
2. 创建 **Token Plan Key** (不是普通的 API Key)
3. 更新环境变量 `MINIMAX_API_KEY`

## API 信息

- **端点**: `POST https://api.minimaxi.com/v1/t2a_v2`
- **模型**: `speech-2.6-hd` (高清) 或 `speech-2.6-turbo` (快速)
- **API Key**: 使用 `${MINIMAX_API_KEY}`

## 使用方式

### 基本调用

```bash
cd ~/.openclaw/workspace/skills/minimax-tts/scripts
./tts.sh "要转换的文本" [输出文件路径]
```

### 参数说明

| 参数 | 必填 | 说明 |
|-----|-----|-----|
| text | ✅ | 要转换的文本（最长 10000 字符） |
| output | ❌ | 输出文件路径，默认 `/tmp/tts_output.mp3` |

### 可用声音 ID

| voice_id | 说明 |
|----------|-----|
| `male-qn-qingse` | 男声-青年-清澈 |
| `female-qn-qingse` | 女声-青年-清澈 |
| `male-qn-baiyan` | 男声-青年-白嫖 |
| `female-qn-baiyan` | 女声-青年-白嫖 |
| `male-tianmei` | 男声-甜妹 |
| `female-tianmei` | 女声-甜妹 |
| `male-yuncong` | 男声-云涌 |
| `female-yuncong` | 女声-云涌 |

## 高级选项

修改 `tts.sh` 脚本中的参数：

- `voice_id`: 选择声音
- `speed`: 语速 (0.5-2.0，默认 1.0)
- `pitch`: 音调 (-50~50，默认 0)
- `emotion`: 情感 (happy, sad, angry, fearful, surprised, neutral)

## 输出

生成的音频文件保存为 MP3 格式，可直接用于播放或发送。

## 示例

```bash
# 基本用法
./tts.sh "你好，这是一个测试"

# 指定输出路径
./tts.sh "欢迎使用语音合成" "/tmp/welcome.mp3"

# 使用特定声音
VOICE_ID=female-tianmei ./tts.sh "你好，我是甜妹"
```
