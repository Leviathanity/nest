#!/bin/bash
# MiniMax Image Generation 脚本
# 用法: ./image.sh "图像描述" [输出文件路径]

set -e

# 配置
API_KEY="${MINIMAX_API_KEY}"
BASE_URL="https://api.minimaxi.com/v1/image_generation"
MODEL="image-01"
ASPECT_RATIO="1:1"

# 参数
PROMPT="$1"
OUTPUT="${2:-/tmp/image_output.jpg}"

if [ -z "$PROMPT" ]; then
    echo "用法: $0 <图像描述> [输出文件路径]"
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
        \"prompt\": \"${PROMPT}\",
        \"aspect_ratio\": \"${ASPECT_RATIO}\"
    }")

# 检查响应
STATUS=$(echo "$RESPONSE" | grep -o '"status_code":[0-9]*' | grep -o '[0-9]*$')

if [ "$STATUS" = "0" ]; then
    # 提取图像 URL (保持原始编码)
    IMAGE_URL=$(echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'data' in data:
    d = data['data']
    if 'image_urls' in d and len(d['image_urls']) > 0:
        print(d['image_urls'][0])
    elif 'url' in d:
        print(d['url'])
" 2>/dev/null) || true
    
    if [ -n "$IMAGE_URL" ]; then
        echo "下载图像中..."
        curl -s -o "$OUTPUT" "$IMAGE_URL"
        
        # 检查文件类型
        FILE_TYPE=$(head -c 10 "$OUTPUT" 2>/dev/null || echo "")
        if [[ "$FILE_TYPE" == *"<?xml"* ]] || [[ "$FILE_TYPE" == *"<Error>"* ]]; then
            echo "错误: 下载失败 - URL 可能已过期"
            cat "$OUTPUT"
            rm -f "$OUTPUT"
            exit 1
        fi
        
        echo "成功: 图像已保存至 $OUTPUT"
        echo "文件大小: $(wc -c < "$OUTPUT") bytes"
    else
        echo "错误: 未能提取图像 URL"
        echo "响应: $RESPONSE"
        exit 1
    fi
else
    ERROR_MSG=$(echo "$RESPONSE" | grep -o '"status_msg":"[^"]*"' | sed 's/"status_msg":"//;s/"$//')
    echo "错误: API 调用失败 - $ERROR_MSG"
    exit 1
fi
