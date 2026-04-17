---
name: minimax-image-understand
description: |
  使用 MiniMax Token Plan MCP 进行图像理解
  支持分析图片内容、提取信息、回答图片相关问题
---

# MiniMax 图像理解技能

## 概述

使用 MiniMax Token Plan MCP 的 `understand_image` 工具进行图像理解和分析。

**前提条件：**
- 已安装 uvx：`curl -LsSf https://astral.sh/uv/install.sh | sh`
- 已配置 `${MINIMAX_API_KEY}` 环境变量（使用 Token Plan API Key）
- API Host 已设置为 `https://api.minimaxi.com`

## 使用方式

### 基本调用

```bash
cd ~/.openclaw/workspace/skills/minimax-image-understand/scripts
./understand.sh "图片问题" "图片URL或本地路径"
```

### 分析示例

```bash
# 分析网络图片
./understand.sh "这张图片里有什么？" "https://example.com/image.jpg"

# 分析本地图片
./understand.sh "描述这张图片的内容" "/path/to/local/image.png"
```

## 参数说明

| 参数 | 必填 | 说明 |
|-----|-----|-----|
| prompt | ✅ | 对图片的提问或分析要求 |
| image_url | ✅ | 图片来源，支持 HTTP/HTTPS URL 或本地文件路径 |

### 支持格式

- JPEG
- PNG
- GIF
- WebP
- 最大 20MB

## 输出

返回 AI 对图片的理解和分析结果。

## 示例

```bash
# 基础分析
./understand.sh "这张图片的主体是什么？" "https://example.com/photo.jpg"

# 详细描述
./understand.sh "请详细描述这张图片的场景、人物、动作等信息" "/tmp/image.png"

# 提取文字
./understand.sh "请提取图片中的所有文字内容" "https://example.com/screenshot.png"
```

## 技术细节

- 使用 MiniMax Coding Plan MCP 的 `minimax-coding-plan-mcp` 包
- 通过 stdio 协议与 MCP 服务器通信
- 支持 URL 和本地文件两种图片来源

## 注意事项

1. 本地图片路径需要是绝对路径
2. 图片文件大小不能超过 20MB
3. 使用 URL 时确保图片可公开访问
