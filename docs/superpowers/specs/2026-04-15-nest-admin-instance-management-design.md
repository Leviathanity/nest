# Nest Admin 实例管理扩展设计

**日期：** 2026-04-15
**版本：** 1.0
**状态：** 已批准

## 1. 目标

扩展 nest-admin 系统，实现多 OpenClaw 实例的完整生命周期管理，包括预制技能仓库、插件仓库、身份模板、模型 Key 集中管理。

## 2. 目录结构

### 2.1 预制内容目录 (`presets/`)

```
nest-admin/configs/presets/
├── keys.json                    # 集中存储所有 API Keys
├── skills/                      # 技能仓库
│   ├── {skill-id}/
│   │   └── SKILL.md
│   └── ...
├── plugins/                     # 插件仓库
│   ├── {plugin-id}/
│   │   ├── config.json          # 插件默认配置
│   │   └── SKILL.md            # 插件技能文件（如有）
│   └── ...
└── identities/                   # 身份模板
    ├── {identity-id}/
    │   ├── SOUL.md
    │   ├── USER.md
    │   ├── IDENTITY.md
    │   ├── HEARTBEAT.md
    │   └── agent.json           # agents/main/agent/ 下的配置文件
    └── ...
```

### 2.2 实例目录结构 (`instances/{name}/`)

每个实例完全模拟 `c:/nest/main` 结构：

```
configs/instances/{name}/
├── openclaw.json                # 主配置
├── agents/
│   └── main/
│       └── agent/
│           ├── auth.json
│           ├── models.json
│           └── auth-profiles.json
├── workspace/
│   ├── AGENTS.md
│   ├── SOUL.md                  # 从 identity 模板复制
│   ├── USER.md                  # 从 identity 模板复制
│   ├── IDENTITY.md              # 从 identity 模板复制
│   ├── HEARTBEAT.md             # 从 identity 模板复制
│   ├── skills/                  # 从 presets/skills 复制
│   │   ├── github/SKILL.md
│   │   └── ...
│   └── memory/
├── skills/                       # 插件技能文件
│   └── {plugin-id}/SKILL.md     # 从 presets/plugins 复制
├── extensions/                  # 插件配置
│   └── {plugin-id}/
│       └── config.json          # 从 presets/plugins 复制
├── memory/
│   └── main.sqlite
├── browser/
│   └── profiles/
├── cron/
│   └── jobs.json
└── logs/
```

## 3. keys.json 结构

```json
{
  "version": 1,
  "keys": {
    "minimax": {
      "apiKey": "sk-xxxx",
      "label": "MiniMax 主账号"
    },
    "feishu": {
      "appId": "cli_xxx",
      "appSecret": "xxx",
      "verificationToken": "xxx",
      "label": "飞书应用"
    },
    "weixin": {
      "enabled": true,
      "label": "企业微信"
    }
  },
  "defaultProvider": "minimax"
}
```

## 4. API 设计

### 4.1 预制内容管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/presets/keys` | 获取所有预制 Keys |
| PUT | `/api/presets/keys` | 更新 Keys |
| GET | `/api/presets/identities` | 获取身份模板列表 |
| GET | `/api/presets/identities/{id}` | 获取身份模板详情（包含文件内容） |
| GET | `/api/presets/skills` | 获取技能列表 |
| GET | `/api/presets/skills/{id}` | 获取技能详情 |
| GET | `/api/presets/plugins` | 获取插件列表 |
| GET | `/api/presets/plugins/{id}` | 获取插件详情 |

### 4.2 实例创建（扩展）

`POST /api/instances` 请求体扩展：

```json
{
  "name": "instance-1",
  "image": "openclaw:pure-gpu",
  "identity": "employee",
  "skills": ["github", "web-search"],
  "plugins": ["feishu"],
  "modelProvider": "minimax",
  "channels": {
    "feishu": true,
    "weixin": false
  }
}
```

### 4.3 响应格式

所有 API 响应使用统一格式：

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

## 5. 创建流程

### 5.1 实例创建步骤

1. **参数验证**
   - 检查实例名唯一性
   - 验证技能/插件/身份 ID 存在
   - 验证模型 Provider 有效

2. **生成配置**
   - 生成 `openclaw.json`：从基础配置开始，合并身份配置、模型配置、渠道配置
   - 从 `presets/keys.json` 注入对应 API Keys
   - 生成 token 用于 Control UI 认证

3. **复制文件**
   - 创建目录结构
   - 复制 `presets/identities/{identity}/*` 到 `instances/{name}/workspace/`
   - 复制 `presets/skills/{skill}/*` 到 `instances/{name}/workspace/skills/`
   - 复制 `presets/plugins/{plugin}/*` 到 `instances/{name}/skills/` 和 `extensions/`

4. **启动容器**
   - 分配网络 IP 和端口
   - 挂载卷（只读模式）
   - 启动后执行初始化脚本

## 6. 微信渠道特殊处理

微信渠道（`openclaw-weixin`）使用二维码配对，不需要在创建时配置 key：

1. 创建实例时在 `plugins` 中添加 `openclaw-weixin`
2. 插件配置文件中设置 `enabled: true`
3. 实例启动后，通过 Control UI 进行二维码配对操作
4. 配对后的凭证存储在实例的 `credentials/` 目录

## 7. 前端表单设计

### 7.1 创建实例页面

```
┌─────────────────────────────────────────────────────────────┐
│ 创建新实例                                                    │
├─────────────────────────────────────────────────────────────┤
│ 实例名称: [___________] (实例ID: 自动分配)                    │
│                                                             │
│ 镜像类型: ( ) GPU  ( ) CPU                                   │
│                                                             │
│ 身份模板: [下拉选择 ▼]                                         │
│   - employee (员工助手)                                       │
│   - manager (管理者)                                         │
│   - developer (开发者)                                        │
│   - empty (空白)                                             │
│                                                             │
│ 预置技能: [✓] GitHub  [✓] Web Search  [ ] Code Gen          │
│                                                             │
│ 预置插件: [ ] 飞书  [✓] 企业微信                              │
│                                                             │
│ 模型提供商: [MiniMax ▼]                                      │
│ API Key: [从预设选择 ▼] 或 [输入新Key]                         │
│                                                             │
│ 渠道配置:                                                    │
│   飞书: [启用] BotToken: [预设继承 ▼]                         │
│   微信: [启用] (二维码配对)                                    │
│                                                             │
│                    [取消]  [创建实例]                         │
└─────────────────────────────────────────────────────────────┘
```

## 8. 配置文件继承关系

```
presets/keys.json
        │
        ▼
presets/identities/{identity}/
  - SOUL.md, USER.md, IDENTITY.md, HEARTBEAT.md
  - agent.json (agents/main/agent/*)
        │
        ▼
instances/{name}/workspace/
instances/{name}/agents/main/agent/
        │
        ▼
openclaw.json (merged)
  - cluster: instance info
  - models: from provider
  - channels: feishu/weixin config
  - plugins: enabled plugins with config
  - env: API keys from presets/keys.json
```

## 9. 安全考虑

1. **Keys 存储**：预制 keys 存储在 nest-admin 的配置目录，应限制访问权限
2. **传输安全**：Keys 在 API 响应中应该脱敏显示（如 `sk-xxxx...xxxx`）
3. **实例隔离**：每个实例有独立 token，实例间不共享认证信息

## 10. 扩展计划

### Phase 1（当前）
- 基础框架和目录结构
- 预制内容管理 API
- 实例创建流程

### Phase 2
- 前端 UI 完善
- 预制内容编辑器

### Phase 3
- Git 仓库同步支持
- 实例快照/备份功能
