---
name: seek翻译平台
description: |
  管理文档翻译平台的翻译任务，包括登录、创建任务、查看进度和下载结果。支持术语库验证和任务状态自动轮询。
  Manage translation tasks for the document translation platform, including login, task creation, progress tracking, and result download. Supports glossary validation and automatic task status polling.
---

> ⚠️ **必须使用子代理模式**
> 
> 由于翻译任务耗时较长（可能需要 30 分钟以上），**必须使用子代理（sub-agent）模式**处理此技能，避免阻塞主会话。
> 
> 使用方式：`sessions_spawn` 创建一个独立会话执行翻译任务，完成后返回结果给用户。

# 文档翻译平台任务管理技能

## 概述

管理文档翻译平台（SeekManager Translation Platform）的翻译任务，包括登录、创建任务、查看进度、下载结果。

**API 文档**: `/docs/openapi.yaml` 可随时查询 API 信息

## 完整流程

### 1. 登录获取 Token
```bash
LOGIN=$(curl -s http://192.168.2.170/api/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}')
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin)['accessToken'])")
```

### 2. 术语库验证（如用户指定）

**获取可用术语库列表**:
```bash
curl -s "http://192.168.2.170/api/glossaries" -H "Authorization: Bearer $TOKEN" | \
  python3 -c "import sys,json; data=json.load(sys.stdin); 
  [print(f'ID: {g[\"id\"]}, Name: {g[\"name\"]}, Entries: {g.get(\"entryCount\",0)}') 
  for g in data['list']]"
```

**验证用户提供的术语库名称**:
- 获取术语库列表后，比对用户给出的名称与 `id` 或 `name` 字段
- 如果找不到匹配的术语库，**不能提交任务**，必须告知用户可用的术语库列表
- 验证通过后，在 complete 步骤使用 `glossaryId` 参数

### 3. 创建翻译任务（两阶段方式）

**第一步：验证文件格式（必须！）**

在上传文件之前，必须验证文件格式是否正确：

```python
import zipfile
import os

def validate_document(file_path):
    """验证文档格式"""
    ext = os.path.splitext(file_path)[1].lower()
    
    # 支持的格式
    VALID_FORMATS = {
        '.docx': 'Word 文档 (Office Open XML)',
        '.xlsx': 'Excel 工作簿 (Office Open XML)',
        '.pptx': 'PowerPoint 演示文稿 (Office Open XML)',
        '.pdf': 'PDF 文档'
    }
    
    if ext not in VALID_FORMATS:
        raise ValueError(f"不支持的文件格式: {ext}。支持的格式: {', '.join(VALID_FORMATS.keys())}")
    
    # 对于 Office 格式（docx/xlsx/pptx），验证是否为有效的 ZIP 文件
    if ext in ['.docx', '.xlsx', '.pptx']:
        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                # 检查必要的文件
                if '[Content_Types].xml' not in z.namelist():
                    raise ValueError(f"无效的 {ext} 文件：缺少必要的 XML 结构")
        except zipfile.BadZipFile:
            raise ValueError(f"无效的文件：不是有效的 {VALID_FORMATS[ext]} 格式（ZIP 格式验证失败）")
    
    # PDF 格式检查（文件头）
    if ext == '.pdf':
        with open(file_path, 'rb') as f:
            header = f.read(5)
            if not header.startswith(b'%PDF-'):
                raise ValueError("无效的 PDF 文件：文件头不正确")
    
    return True

# 使用示例
validate_document('/path/to/document.docx')
print("✅ 文件格式验证通过")
```

**支持的格式**：

| 扩展名 | 文件类型 | 验证方式 |
|--------|----------|----------|
| `.docx` | Word 文档 | ZIP 格式 + [Content_Types].xml |
| `.xlsx` | Excel 工作簿 | ZIP 格式 + [Content_Types].xml |
| `.pptx` | PowerPoint 演示文稿 | ZIP 格式 + [Content_Types].xml |
| `.pdf` | PDF 文档 | 文件头检查 %PDF- |

**重要**：
- ❌ 不支持 `.doc`、`.xls`、`.ppt`（旧版 Office 格式）
- ❌ 不支持纯文本文件（如 .txt）
- ❌ 不支持 Markdown 文件（如 .md）
- 如果文件验证失败，**不能上传**，必须告知用户文件格式问题

**第二阶段：init 上传文件**
```bash
curl -s "http://192.168.2.170/api/tasks/init" -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@/path/to/document.docx" \
  -F "sourceLang=zh-CN" \
  -F "targetLang=en-US"
```
返回 batchId，**必须记录**

**第二阶段：complete 确认**
```bash
curl -s "http://192.168.2.170/api/tasks/complete" -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "batchId": "20260222_abc123",
    "sourceLang": "zh-CN",
    "targetLang": "en-US",
    "glossaryId": "术语库ID（验证通过后）"
  }'
```

### 4. 任务状态轮询（重要！）

**提交后必须按以下规则轮询**：

| 时间点 | 操作 |
|--------|------|
| 提交后 1 分钟 | 检查任务状态 |
| 之后每 1 分钟 | 再次检查 |
| 30 分钟仍未完成 | **通知用户**任务仍在处理中 |
| 60 分钟仍未完成 | 再次通知，询问是否继续等待 |

**检查任务状态（必须使用单个任务详情 API）**:
```bash
# ⚠️ 不要使用任务列表 API，状态可能不准确！
# 必须使用单个任务详情 API: GET /api/tasks/{batchId}
curl -s "http://192.168.2.170/api/tasks/YOUR_BATCH_ID" -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys,json
task = json.load(sys.stdin)
# 外层 status 可能不准确，要看 task['arg']['status']
print(f\"外层Status: {task['status']}\")
print(f\"实际Status: {task['arg']['status']}\")
print(f\"Started: {task['arg'].get('started_at')}\")
print(f\"Completed: {task['arg'].get('completed_at')}\")
print(f\"HasResult: {task.get('hasResult')}\")"
```

**任务状态值**: 
- 外层 `status`: `queued` / `processing`（不一定准确）
- 实际状态: `task['arg']['status']`: `queued` → `processing` → `completed` / `failed`
- 完成后 `hasResult: true` 表示有结果可下载

### 5. 下载翻译结果
```bash
FILENAME=$(python3 -c "import urllib.parse; print(urllib.parse.quote('文档.docx'))")
curl -s "http://192.168.2.170/api/tasks/YOUR_BATCH_ID/download/${FILENAME}?createdAt=2026-02-22T10:00:00Z" \
  -H "Authorization: Bearer $TOKEN" -o translated.docx
```

**注意**: 下载时需要知道任务的 `createdAt` 时间戳，可在任务详情中获取。

## 关键点

1. **必须使用 batchId**：创建任务后返回的 batchId 是后续操作的唯一标识
2. **两阶段方式**：必须先 init 上传文件，再 complete 确认创建任务
3. **字段名是 files**：上传文件时使用 `files` 字段名，不是 `file`
4. **术语库验证**：用户指定术语库时，必须先验证存在再提交
5. **状态轮询**：提交后每1分钟检查，30分钟未完成必须通知用户
6. **createdAt 参数**：下载时需要提供创建时间戳
7. **发送文件给用户**：翻译完成后，必须使用 message 工具发送翻译好的文件给用户

## 步骤 6：发送翻译结果给用户（必须）

翻译完成后，必须使用 message 工具将翻译好的文件发送给当前用户：

```python
# 使用 message 工具发送文件给用户
message(
    action="send",
    filePath="/path/to/translated.docx",
    message="翻译完成！请查收。"
)
```

**发送对象**：当前对话的用户（通过飞书/其他渠道发送消息的用户）

## 语言代码
- zh-CN：中文
- en-US：英语
- 其他: ja-JP, ko-KR, fr-FR, de-DE, es-ES, ru-RU 等

## 术语库列表参考

当前平台的术语库（通过 `GET /api/glossaries` 获取）:
- `ccc` - ccc (1 entry)
- `auto_parts` - ggg (3 entries)  
- `e2e_test_auto_parts` - aaa (10 entries)
- `my_glossary` - 我的术语库
- `new_energy_vehicle_parts` - full (197 entries) - 新能源汽车术语

如需使用术语库，请在任务提交时提供 `glossaryId`。
