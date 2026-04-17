---
name: minimax-search
description: |
  使用 MiniMax Token Plan MCP 进行网络搜索
  支持并行多查询搜索，返回搜索结果摘要
---

# MiniMax 网络搜索技能

## 概述

使用 MiniMax Token Plan MCP 的 `web_search` 工具进行网络搜索。

**前提条件：**
- 已安装 uvx：`curl -LsSf https://astral.sh/uv/install.sh | sh`
- 已配置 `${MINIMAX_API_KEY}` 环境变量（使用 Token Plan API Key）
- API Host 已设置为 `https://api.minimaxi.com`

## 使用方式

### 基本调用

```bash
cd ~/.openclaw/workspace/skills/minimax-search/scripts
./search.sh "搜索关键词"
```

### 并行多查询

```bash
cd ~/.openclaw/workspace/skills/minimax-search/scripts
./search.sh "关键词1" "关键词2" "关键词3"
```

### 参数说明

| 参数 | 必填 | 说明 |
|-----|-----|-----|
| queries | ✅ | 搜索关键词（支持多个，用空格分隔） |

### 输出

返回搜索结果，包括：
- 标题
- URL 链接
- 摘要snippet

## 示例

```bash
# 单次搜索
./search.sh "什么是CRM系统"

# 并行多查询
./search.sh "CRM教育行业" "教育培训CRM功能" "教育培训机构管理系统"
```

## 技术细节

- 使用 MiniMax Coding Plan MCP 的 `minimax-coding-plan-mcp` 包
- 通过 stdio 协议与 MCP 服务器通信
- 支持 Google 高级搜索语法（如 `site:example.com`、`intitle:keyword`）

## 注意事项

1. 搜索结果为英文引擎返回，中文查询可能需要用英文关键词
2. 并行查询可以同时搜索多个不相关的关键词
3. 使用 Google 高级搜索语法可以精确化搜索结果
