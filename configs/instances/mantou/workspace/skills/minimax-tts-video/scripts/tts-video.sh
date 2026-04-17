#!/bin/bash
# MiniMax TTS 语音视频合成脚本
# 将 TTS 语音与视频合并，通过微信发送

set -e

# 配置
TTS_MODEL="${TTS_MODEL:-speech-2.8-hd}"
TTS_VOICE="${TTS_VOICE:-male-qn-qingse}"
API_KEY="${MINIMAX_API_KEY}"
BASE_URL="https://api.minimaxi.com/v1/t2a_v2"

# 参数
TEXT="$1"
OUTPUT="${2:-/tmp/tts_video.mp4}"

if [ -z "$TEXT" ]; then
    echo "用法: $0 <文本> [输出MP4路径]"
    exit 1
fi

if [ -z "$API_KEY" ]; then
    echo "错误: MINIMAX_API_KEY 未设置"
    exit 1
fi

TTS_OUTPUT="/tmp/tts_audio_$$.mp3"

echo "生成 TTS 语音..."
# 调用 MiniMax TTS API
RESPONSE=$(curl -s -X POST "${BASE_URL}" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"${TTS_MODEL}\",
        \"text\": \"${TEXT}\",
        \"stream\": false,
        \"voice_setting\": {
            \"voice_id\": \"${TTS_VOICE}\",
            \"speed\": 1,
            \"pitch\": 0,
            \"emotion\": \"happy\"
        },
        \"audio_setting\": {
            \"sample_rate\": 32000,
            \"format\": \"mp3\",
            \"channel\": 1
        }
    }")

# 检查响应
STATUS=$(echo "$RESPONSE" | grep -o '"status_code":[0-9]*' | grep -o '[0-9]*$')

if [ "$STATUS" != "0" ]; then
    ERROR_MSG=$(echo "$RESPONSE" | grep -o '"status_msg":"[^"]*"' | sed 's/"status_msg":"//;s/"$//')
    echo "错误: TTS API 调用失败 - $ERROR_MSG"
    exit 1
fi

# 提取音频 hex 数据并转换为 MP3
AUDIO_HEX=$(echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'data' in data and 'audio' in data['data']:
    print(data['data']['audio'])
" 2>/dev/null) || true

if [ -n "$AUDIO_HEX" ]; then
    python3 -c "
import sys
hex_data = sys.stdin.read().strip()
byte_data = bytes.fromhex(hex_data)
with open('${TTS_OUTPUT}', 'wb') as f:
    f.write(byte_data)
" <<< "$AUDIO_HEX"
    echo "TTS 语音已保存: ${TTS_OUTPUT}"
else
    echo "错误: 未能提取音频数据"
    exit 1
fi

# 获取音频时长
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${TTS_OUTPUT}" 2>/dev/null || echo "7")
echo "音频时长: ${DURATION}秒"

# 生成视频并合并音频
echo "生成视频..."
ffmpeg -f lavfi -i "color=c=blue:s=320x240:d=${DURATION}" \
       -i "${TTS_OUTPUT}" \
       -c:v libx264 -preset ultrafast \
       -c:a aac -b:a 128k \
       -shortest \
       "${OUTPUT}" -y 2>/dev/null

if [ -f "${OUTPUT}" ]; then
    echo "成功: 视频已保存至 ${OUTPUT}"
    echo "文件大小: $(wc -c < "${OUTPUT}") bytes"
    
    # 验证音轨
    AUDIO_DURATION=$(ffprobe -v error -show_entries stream=codec_type,duration -of default=noprint_wrappers=1 "${OUTPUT}" 2>/dev/null | grep "audio" -A 1 | tail -1 || echo "unknown")
    echo "视频音轨时长: ${AUDIO_DURATION}秒"
else
    echo "错误: 视频生成失败"
    exit 1
fi

# 清理临时文件
rm -f "${TTS_OUTPUT}"

echo "完成!"
echo "发送命令: message --action=send --channel=openclaw-weixin --media=${OUTPUT}"
