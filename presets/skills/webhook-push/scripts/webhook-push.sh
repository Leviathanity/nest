#!/bin/bash
# Webhook Push 脚本 - 推送到飞书机器人

# 默认配置
WEBHOOK_URL="${WEBHOOK_URL:-https://open.feishu.cn/open-apis/bot/v2/hook/78b9f4b9-12e8-4c14-9098-c367d5180399}"
EVENTS_FILE="${EVENTS_FILE:-/tmp/opencode-events.jsonl}"
LAST_EVENT_FILE="${LAST_EVENT_FILE:-/tmp/webhook-push-last-event}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 发送文本消息
send_text() {
    local message="$1"
    if [ -z "$message" ]; then
        log_error "消息内容不能为空"
        return 1
    fi
    
    curl -s -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"msg_type\": \"text\",
            \"content\": {
                \"text\": \"$message\"
            }
        }"
    
    if [ $? -eq 0 ]; then
        log_info "消息发送成功"
        return 0
    else
        log_error "消息发送失败"
        return 1
    fi
}

# 发送富文本消息（带标题）
send_notify() {
    local title="$1"
    local content="$2"
    
    if [ -z "$title" ] || [ -z "$content" ]; then
        log_error "标题和内容不能为空"
        return 1
    fi
    
    # 转义内容中的特殊字符
    local escaped_content=$(echo "$content" | sed 's/"/\\"/g' | sed 's/\n/\\n/g')
    local escaped_title=$(echo "$title" | sed 's/"/\\"/g')
    
    curl -s -X POST "$WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"msg_type\": \"post\",
            \"content\": {
                \"post\": {
                    \"zh_cn\": {
                        \"title\": \"$escaped_title\",
                        \"content\": [[{\"tag\": \"text\", \"text\": \"$escaped_content\"}]]
                    }
                }
            }
        }"
    
    if [ $? -eq 0 ]; then
        log_info "富文本消息发送成功"
        return 0
    else
        log_error "富文本消息发送失败"
        return 1
    fi
}

# 轮询 OpenCode 事件并推送
poll_opencode() {
    log_info "开始轮询 OpenCode 事件..."
    
    while true; do
        if [ -f "$EVENTS_FILE" ]; then
            # 获取最新事件
            local latest_event=$(tail -1 "$EVENTS_FILE" 2>/dev/null)
            
            if [ -n "$latest_event" ]; then
                # 检查是否是 新事件
                if [ -f "$LAST_EVENT_FILE" ]; then
                    local last_event=$(cat "$LAST_EVENT_FILE")
                    if [ "$latest_event" != "$last_event" ]; then
                        log_info "检测到新事件: $latest_event"
                        send_text "$latest_event"
                        echo "$latest_event" > "$LAST_EVENT_FILE"
                    fi
                else
                    # 首次运行，只记录不推送
                    echo "$latest_event" > "$LAST_EVENT_FILE"
                    log_info "初始化事件记录: $latest_event"
                fi
            fi
        else
            log_error "事件文件不存在: $EVENTS_FILE"
        fi
        
        sleep 30
    done
}

# 主命令处理
case "$1" in
    send)
        send_text "$2"
        ;;
    notify)
        send_notify "$2" "$3"
        ;;
    poll)
        poll_opencode
        ;;
    test)
        send_text "OpenClaw Webhook 测试消息"
        ;;
    *)
        echo "用法: $0 {send|notify|poll|test} [参数]"
        echo ""
        echo "命令:"
        echo "  send <message>    发送文本消息"
        echo "  notify <title> <content>  发送富文本消息"
        echo "  poll             轮询 OpenCode 事件并推送"
        echo "  test             发送测试消息"
        exit 1
        ;;
esac
