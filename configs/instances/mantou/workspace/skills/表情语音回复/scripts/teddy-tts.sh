#!/bin/bash
# 泰迪熊 TTS 语音视频合成脚本
# 根据文本内容自动选择合适的泰迪熊表情

set -e

# 路径配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EMOJI_DIR="${SCRIPT_DIR}/../emoji"
TTS_API_URL="https://api.minimaxi.com/v1/t2a_v2"

# 配置
API_KEY="${MINIMAX_API_KEY}"
TTS_MODEL="${TTS_MODEL:-speech-2.8-hd}"
TTS_VOICE="${TTS_VOICE:-male-qn-qingse}"

# 参数
TEXT="$1"
EMOTION="$2"  # 可选，如 01, 02 等
OUTPUT="$3"    # 可选，输出文件路径

if [ -z "$TEXT" ]; then
    echo "用法: $0 <文本> [表情编号] [输出文件]"
    echo ""
    echo "表情编号："
    echo "  01 - 开心    适合问候、感谢"
    echo "  02 - 思考    适合分析问题"
    echo "  03 - 惊讶    适合意外消息"
    echo "  04 - 犯困    适合休息话题"
    echo "  05 - 兴奋    适合庆祝"
    echo "  06 - 害羞    适合尴尬场景"
    echo "  07 - 得意    适合骄傲炫耀"
    echo "  08 - 饥饿    适合美食话题"
    echo "  09 - 耍酷    适合耍帅场景"
    echo "  10 - 爱心    适合表达喜欢"
    exit 1
fi

# 如果没有指定输出文件
if [ -z "$OUTPUT" ]; then
    OUTPUT="/tmp/teddy_tts_$$.mp4"
fi

# 自动选择表情函数
auto_select_emotion() {
    local text="$1"
    local emotion="01"  # 默认开心
    
    # 转换为小写便于匹配
    local lower=$(echo "$text" | tr '[:upper:]' '[:lower:]')
    
    case "$lower" in
        *思考*|*分析*|*因为*|*所以*|*但是*|*考虑*|*怎么*|*为什么*)
            emotion="02" ;;
        *惊讶*|*竟然*|*居然*|*没想到*|*不会吧*|*什么*|*真的吗*)
            emotion="03" ;;
        *困*|*累了*|*休息*|*睡觉*|*好累*|*眯*)
            emotion="04" ;;
        *太棒*|*恭喜*|*庆祝*|*兴奋*|*太好了*|*哇*|*耶*)
            emotion="05" ;;
        *不好意*|*尴尬*|*害羞*|*脸红*)
            emotion="06" ;;
        *厉害*|*骄傲*|*得意*|*佩服*|*棒*)
            emotion="07" ;;
        *饿*|*吃饭*|*美食*|*想吃*|*好吃*)
            emotion="08" ;;
        *酷*|*帅气*|*帅*|*耍酷*)
            emotion="09" ;;
        *喜欢*|*爱*|*爱你*|*心*|*么么哒*)
            emotion="10" ;;
        *)
            emotion="01" ;;
    esac
    
    echo "$emotion"
}

# 选择表情
if [ -z "$EMOTION" ]; then
    EMOTION=$(auto_select_emotion "$TEXT")
fi

# 格式化表情编号
EMOTION=$(printf "%02d" "$EMOTION")

# 表情图片路径
EMOJI_FILE="${EMOJI_DIR}/t_${EMOTION}.png"

if [ -z "$EMOJI_FILE" ] || [ ! -f "$EMOJI_FILE" ]; then
    echo "错误: 找不到表情图片: ${EMOJI_DIR}/teddy_${EMOTION}_*.png"
    exit 1
fi

echo "选择表情: ${EMOTION} -> ${EMOJI_FILE}"

# 临时文件
TTS_OUTPUT="/tmp/teddy_tts_audio_$$.mp3"
IMAGE_SCALED="/tmp/teddy_scaled_$$.png"

# 1. 生成 TTS 语音
echo "生成语音..."
RESPONSE=$(curl -s -X POST "${TTS_API_URL}" \
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

STATUS=$(echo "$RESPONSE" | grep -o '"status_code":[0-9]*' | grep -o '[0-9]*$')

if [ "$STATUS" != "0" ]; then
    ERROR_MSG=$(echo "$RESPONSE" | grep -o '"status_msg":"[^"]*"' | sed 's/"status_msg":"//;s/"$//')
    echo "错误: TTS API 调用失败 - $ERROR_MSG"
    exit 1
fi

AUDIO_HEX=$(echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'data' in data and 'audio' in data['data']:
    print(data['data']['audio'])
" 2>/dev/null) || true

if [ -z "$AUDIO_HEX" ]; then
    echo "错误: 未能提取音频数据"
    exit 1
fi

python3 -c "
import sys
hex_data = sys.stdin.read().strip()
byte_data = bytes.fromhex(hex_data)
with open('${TTS_OUTPUT}', 'wb') as f:
    f.write(byte_data)
" <<< "$AUDIO_HEX"

echo "语音已生成: ${TTS_OUTPUT}"

# 2. 缩放表情图片到视频尺寸
echo "处理表情图片..."
ffmpeg -i "${EMOJI_FILE}" -vf scale=320:240 "${IMAGE_SCALED}" -y 2>/dev/null

# 3. 获取音频时长
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "${TTS_OUTPUT}" 2>/dev/null || echo "5")
echo "音频时长: ${DURATION}秒"

# 4. 生成视频
echo "生成视频..."
ffmpeg -loop 1 \
       -i "${IMAGE_SCALED}" \
       -i "${TTS_OUTPUT}" \
       -c:v libx264 -preset ultrafast -tune stillimage \
       -c:a aac -b:a 128k \
       -shortest \
       -t "${DURATION}" \
       "${OUTPUT}" -y 2>/dev/null

# 清理临时文件
rm -f "${TTS_OUTPUT}" "${IMAGE_SCALED}"

if [ -f "${OUTPUT}" ]; then
    echo "成功: ${OUTPUT}"
    echo "文件大小: $(wc -c < "${OUTPUT}") bytes"
else
    echo "错误: 视频生成失败"
    exit 1
fi
