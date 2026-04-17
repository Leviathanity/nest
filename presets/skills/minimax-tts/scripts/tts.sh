#!/bin/bash
# MiniMax TTS (Text-to-Speech) 脚本
# 用法: ./tts.sh "文本" [输出文件路径]

set -e

# 配置
API_KEY="${MINIMAX_API_KEY}"
BASE_URL="https://api.minimaxi.com/v1/t2a_v2"
MODEL="speech-2.8-hd"
VOICE_ID="male-qn-qingse"
SPEED=1
PITCH=0
EMOTION="happy"
SAMPLE_RATE=32000
FORMAT="mp3"

# 参数
TEXT="$1"
OUTPUT="${2:-/tmp/tts_output.mp3}"

if [ -z "$TEXT" ]; then
    echo "用法: $0 <文本> [输出文件路径]"
    exit 1
fi

if [ -z "$API_KEY" ]; then
    echo "错误: MINIMAX_API_KEY 未设置"
    exit 1
fi

# 调用 API
RESPONSE=$(curl -s -X POST "${BASE_URL}" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"${MODEL}\",
        \"text\": \"${TEXT}\",
        \"stream\": false,
        \"voice_setting\": {
            \"voice_id\": \"${VOICE_ID}\",
            \"speed\": ${SPEED},
            \"pitch\": ${PITCH},
            \"emotion\": \"${EMOTION}\"
        },
        \"audio_setting\": {
            \"sample_rate\": ${SAMPLE_RATE},
            \"format\": \"${FORMAT}\",
            \"channel\": 1
        }
    }")

# 检查响应
STATUS=$(echo "$RESPONSE" | grep -o '"status_code":[0-9]*' | grep -o '[0-9]*$')

if [ "$STATUS" = "0" ]; then
    # 提取 hex 音频数据并转换为 MP3
    AUDIO_HEX=$(echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'data' in data and 'audio' in data['data']:
    print(data['data']['audio'])
" 2>/dev/null) || true
    
    if [ -n "$AUDIO_HEX" ]; then
        # 使用 Python 进行 hex 到二进制的转换
        python3 -c "
import sys
hex_data = sys.stdin.read().strip()
byte_data = bytes.fromhex(hex_data)
with open('$OUTPUT', 'wb') as f:
    f.write(byte_data)
print('done')
" <<< "$AUDIO_HEX"
        echo "成功: 音频已保存至 $OUTPUT"
        echo "文件大小: $(wc -c < "$OUTPUT") bytes"
    else
        echo "错误: 未能提取音频数据"
        echo "响应: $RESPONSE"
        exit 1
    fi
else
    ERROR_MSG=$(echo "$RESPONSE" | grep -o '"status_msg":"[^"]*"' | sed 's/"status_msg":"//;s/"$//')
    echo "错误: API 调用失败 - $ERROR_MSG"
    exit 1
fi
