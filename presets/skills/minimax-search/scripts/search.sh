#!/bin/bash
# MiniMax Token Plan MCP - Web Search Tool
# 使用 Python MCP 客户端进行网络搜索

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 从环境变量或配置文件获取 API Key
if [ -z "$MINIMAX_API_KEY" ]; then
    MINIMAX_API_KEY=$(cat ~/.openclaw/openclaw.json 2>/dev/null | grep -o '"MINIMAX_API_KEY"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*: *"\([^"]*\)"/\1/')
fi

export MINIMAX_API_KEY="${MINIMAX_API_KEY:-}"
export MINIMAX_API_HOST="${MINIMAX_API_HOST:-https://api.minimaxi.com}"

# 检查参数
if [ $# -eq 0 ]; then
    echo "Usage: $0 <query> [query2] [query3] ..."
    echo "Example: $0 \"什么是CRM系统\""
    echo "Example: $0 \"CRM功能\" \"教育行业CRM\""
    exit 1
fi

# 调用 Python MCP 客户端
cd "$SCRIPT_DIR"
exec python3 mcp_client.py "$@"
