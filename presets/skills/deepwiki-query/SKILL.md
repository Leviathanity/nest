---
name: deepwiki-query
description: 使用浏览器访问DeepWiki查询任何GitHub仓库的AI驱动文档和代码理解（必须使用浏览器，因为页面是动态的无法从URL直接获取信息）
availableArgs:
  - name: repo
    description: GitHub仓库地址，可以是完整URL(https://github.com/owner/repo)或owner/repo格式。如果只知道项目名称，可以通过网络搜索获取准确地址
    required: true
  - name: question
    description: 要询问关于该仓库的问题
    required: true
---

# DeepWiki Query Skill

使用浏览器访问 DeepWiki (deepwiki.com) 查询任何 GitHub 仓库的 AI 驱动文档和代码理解。

## ⚠️ 重要要求

1. **必须使用浏览器访问** - DeepWiki 是完全动态的 SPA 页面，无法通过 URL 直接获取有意义的信息
2. **仓库地址获取** - 如果只提供项目名称，需要先通过网络搜索获取准确的 GitHub 地址
3. **使用浏览器工具** - 必须使用 `browser` 工具进行交互

## 使用流程

1. **获取仓库地址**（如需要）
   - 如果用户只提供项目名称，先使用 web_search 搜索获取准确 GitHub 地址
   - 格式：`site:github.com 项目名`

2. **打开 DeepWiki**
   - 使用 browser 工具打开 https://deepwiki.com
   - 等待页面完全加载

3. **搜索仓库**
   - 在搜索框中输入 GitHub 仓库地址（格式：owner/repo）
   - 按 Enter 或点击搜索结果

4. **等待页面加载**
   - DeepWiki 会加载仓库文档
   - 页面包含左侧导航栏（文档结构）和右侧内容区

5. **提问**
   - 使用页面底部的浮窗输入问题
   - 等待 AI 生成回答
   - 获取答案及相关代码引用

## 示例

### 示例 1：已知仓库地址
```
- 仓库: anomalyco/opencode
- 问题: 这个项目的架构是怎样的？
```

### 示例 2：需先搜索获取地址
```
用户说: "查询 opencode 项目的 skill 系统"
步骤:
1. 先搜索: site:github.com opencode skill
2. 获取准确地址: anomalyco/opencode
3. 然后访问 DeepWiki 提问
```

## 技术细节

- DeepWiki 使用 AI 分析 GitHub 仓库并生成交互式文档
- 支持通过对话方式提问，带有实际源代码引用
- 支持多种编程语言和框架
- 页面完全动态加载，必须通过浏览器交互

## 注意事项

- 首次查询仓库可能需要较长时间（DeepWiki 需要索引仓库）
- 可以追问后续问题
- 回答会包含相关源代码文件的链接
- 如果页面未完全加载，等待后再提问
