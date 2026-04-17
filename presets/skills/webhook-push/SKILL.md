---
name: webhook-push
description: 轮询指定来源获取新信息，并通过 webhook 推送到飞书机器人
---

# Webhook Push 技能

将轮询获取的信息通过 webhook 推送到指定目标（支持飞书机器人）。

## 配置

环境变量:
- `WEBHOOK_URL` - Webhook 地址（默认: 用户的飞书 webhook）
- `POLL_SOURCE` - 轮询来源类型（opencode/custom）
- `POLL_INTERVAL` - 轮询间隔（默认: 30 秒）

## 功能

### 1. 发送文本消息到飞书 Webhook

```bash
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "msg_type": "text",
    "content": {
      "text": "消息内容"
    }
  }'
```

### 2. 发送富文本消息

```bash
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "msg_type": "post",
    "content": {
      "post": {
        "zh_cn": {
          "title": "标题",
          "content": [["{""tag"":""text"",""text"":""内容""}"`
        ]
      }
    }
  }'
```

### 3. 轮询 OpenCode 事件并推送

```bash
# 检查是否有新事件
LATEST_EVENT=$(cat /tmp/opencode-events.jsonl 2>/dev/null | tail -1)
if [ -n "$LATEST_EVENT" ]; then
  # 发送到飞书
  curl -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{\"msg_type\": \"text\", \"content\": {\"text\": \"$LATEST_EVENT\"}}"
fi
```

## 使用示例

### 从命令行推送消息

```bash
# 设置 webhook URL
export WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-id"

# 发送文本消息
./scripts/webhook-push.sh send "测试消息"

# 发送带标题的消息
./scripts/webhook-push.sh notify "新事件" "事件内容"
```

### 在 OpenClaw 中使用

```
使用 webhook-push 技能将新信息推送到飞书：
- 设置 WEBHOOK_URL 环境变量
- 调用 send 或 notify 函数发送消息
```

## 飞书 Webhook 消息格式

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| text | 纯文本 | 简单通知 |
| post | 富文本 | 复杂格式 |
| image | 图片 | 带图片通知 |
| interactive | 卡片 | 交互式消息 |

## 注意事项

1. 飞书 webhook 每个机器人每分钟最多发送 20 条消息
2. 消息内容大小限制：1024 字节（文本）
3. 需要确保 WEBHOOK_URL 正确且机器人已启用
