#!/bin/bash
# MiniMax Token Plan MCP - Image Understanding Tool
# 使用 Python MCP 客户端进行图像理解

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 从环境变量或配置文件获取 API Key
if [ -z "$MINIMAX_API_KEY" ]; then
    MINIMAX_API_KEY=$(cat ~/.openclaw/openclaw.json 2>/dev/null | grep -o '"MINIMAX_API_KEY"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"\([^"]*\)"/\1/')
fi

export MINIMAX_API_KEY="${MINIMAX_API_KEY:-}"
export MINIMAX_API_HOST="${MINIMAX_API_HOST:-https://api.minimaxi.com}"

# 检查参数
if [ $# -lt 2 ]; then
    echo "Usage: $0 <prompt> <image_url_or_path>"
    echo "Example: $0 \"这张图片里有什么？\" \"https://example.com/image.jpg\""
    echo "Example: $0 \"描述这张图片\" \"/path/to/local/image.png\""
    exit 1
fi

# 调用 Python MCP 客户端
cd "$SCRIPT_DIR"
exec python3 mcp_client.py "$@"
