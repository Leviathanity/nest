# 实例文件夹结构重构设计

**日期**: 2026-04-18
**状态**: 已批准
**基于**: 2026-04-18-create-instance-design.md (方案 A 修正版)

## 概述

当前实例配置结构将技能和身份文件放在 `presets/` 目录下，这与 OpenClaw 标准目录结构不一致。本设计将重构实例文件夹结构，使其符合 OpenClaw 官方规范：

- **身份文件**在 `workspace/` 下（不是 `/identity`）
- **凭证文件**在 `identity/` 下（设备凭证）
- **技能文件**从 `presets/skills/` 移至 `skills/`

## 目标结构

实例容器内的 `/root/.openclaw/` 目录结构：

```
~/.openclaw/                    # OpenClaw 根目录 (容器内 /root/.openclaw)
├── openclaw.json              # 主配置文件
├── identity/                  # 设备凭证
│   ├── device.json
│   └── device-auth.json
├── workspace/                 # 工作区（身份文件在这里！）
│   ├── IDENTITY.md
│   ├── SOUL.md
│   ├── HEARTBEAT.md
│   ├── USER.md
│   ├── AGENTS.md
│   ├── BOOTSTRAP.md
│   ├── MEMORY.md
│   ├── TOOLS.md
│   ├── skills/               # Workspace 级技能
│   ├── memory/               # 记忆文件
│   ├── docs/
│   └── (其他工作文件)
├── skills/                    # 全局技能
│   └── {skill-name}/
│       └── SKILL.md
├── extensions/                # 扩展
│   └── {plugin_id}/
├── memory/                    # 记忆数据库
│   └── main.sqlite
├── browser/                   # 浏览器数据
├── media/                     # 媒体
└── logs/                      # 日志
```

主机上的实例配置目录 `configs/instances/{name}/`：

```
configs/instances/{name}/           # 主机配置目录
├── openclaw.json                  # 主配置
├── docker-compose.yml             # 实例 compose 文件
├── identity/                      # 设备凭证（挂载到容器）
│   ├── device.json
│   └── device-auth.json
├── workspace/                     # 工作区
│   ├── IDENTITY.md
│   ├── SOUL.md
│   ├── HEARTBEAT.md
│   ├── USER.md
│   ├── AGENTS.md
│   ├── BOOTSTRAP.md
│   ├── MEMORY.md
│   ├── TOOLS.md
│   ├── skills/                    # Workspace 级技能
│   └── memory/                    # 记忆文件
├── skills/                        # 全局技能
│   └── {skill_id}/
│       └── SKILL.md
└── extensions/                     # 扩展
    └── {plugin_id}/
```

## 关键变更点

### 1. 技能目录重组

| 变更前 | 变更后 |
|--------|--------|
| `presets/skills/{skill_id}/` | `skills/{skill_id}/` |
| `/app/presets/skills/` (容器内) | `/root/.openclaw/skills/` (容器内) |

### 2. 身份文件位置

| 变更前 | 变更后 |
|--------|--------|
| `presets/identities/{identity_id}/` | `workspace/` |
| 复制到 `/app/presets/identities/` | 直接使用 `/root/.openclaw/workspace/` |

身份模板文件（IDENTITY.md, SOUL.md 等）直接复制到实例的 `workspace/` 目录。

### 3. 凭证目录

新增 `identity/` 目录用于存放设备凭证：
- `identity/device.json` - 设备信息
- `identity/device-auth.json` - 设备认证信息

### 4. 目录结构对比

| 路径类型 | 变更前 | 变更后 |
|----------|--------|--------|
| 主机配置根目录 | `configs/instances/{name}/` | `configs/instances/{name}/` |
| 主机技能目录 | `configs/instances/{name}/presets/skills/` | `configs/instances/{name}/skills/` |
| 主机身份目录 | `configs/instances/{name}/presets/identities/` | `configs/instances/{name}/workspace/` |
| 容器技能路径 | `/app/presets/skills/{id}` | `/root/.openclaw/skills/{id}` |
| 容器身份路径 | `/app/presets/identities/{id}/` | `/root/.openclaw/workspace/` |
| 容器工作区根路径 | (无) | `/root/.openclaw/workspace/` |

## compose 挂载变更

### 变更前

```yaml
volumes:
  - ./configs/instances/{name}:/app/configs/instance:ro
  - ./configs/instances/{name}/presets:/app/presets:ro
```

### 变更后

```yaml
volumes:
  - ./configs/instances/{name}:/root/.openclaw:ro
  - ./configs/base:/app/configs/base:ro
  - ./configs/presets/extensions/{plugin_id}:/root/.openclaw/extensions/{plugin_id}:ro
```

关键变更：
- 主挂载点从 `/app/configs/instance` 改为 `/root/.openclaw`
- 不再挂载 `presets/` 目录，而是直接挂载整个实例配置目录
- 技能和身份文件直接位于 `/root/.openclaw/` 下

## 后端代码修改点

### 文件：`est-admin/backend/main.py`

#### 1. `copy_presets_to_instance` 函数重构

```python
def copy_presets_to_instance(instance_name: str, identity: str, skills: list):
    """复制预设文件到实例目录"""
    instance_dir = CONFIG_INSTANCES_DIR / instance_name
    
    # 复制身份文件到 workspace/
    if identity and identity != "empty":
        identity_src = PRESETS_DIR / "identities" / identity
        identity_dst = instance_dir / "workspace"
        if identity_src.exists():
            for f in identity_src.iterdir():
                if f.is_file():
                    shutil.copy2(f, identity_dst / f.name)
    
    # 复制技能文件到 skills/
    for skill_id in skills:
        skill_src = PRESETS_DIR / "skills" / skill_id
        skill_dst = instance_dir / "skills" / skill_id
        if skill_src.exists():
            shutil.copytree(skill_src, skill_dst, dirs_exist_ok=True)
```

#### 2. `add_service_to_compose` 函数修改

```python
volumes_list = [
    f"{volume_name}:/root/.openclaw",
    f"./configs/base:/app/configs/base:ro",
]
```

移除：
```python
f"./configs/instances/{name}:/app/configs/instance:ro",
f"./configs/instances/{name}/presets:/app/presets:ro"
```

#### 3. openclaw.json 配置中的技能路径

变更前：
```python
"skills": [f"/app/presets/skills/{s}" for s in (data.skills or [])]
```

变更后：
```python
"skills": [f"/root/.openclaw/skills/{s}" for s in (data.skills or [])]
```

#### 4. 凭证目录创建

在 `create_instance` 函数中添加：
```python
# 创建 identity 目录（设备凭证）
identity_dir = instance_dir / "identity"
identity_dir.mkdir(parents=True, exist_ok=True)
# 生成设备凭证文件
(identity_dir / "device.json").write_text(json.dumps({
    "deviceId": f"device-{name}",
    "instanceName": name
}, indent=2))
```

## 前端修改点

### 文件：`est-admin/frontend/index.html`

前端基本不需要修改，因为：

1. **API 接口不变** - `/api/instances` 等接口保持不变
2. **预设加载逻辑不变** - `/api/presets/skills` 和 `/api/presets/identities` 保持不变
3. **创建实例请求格式不变** - 前端传递的参数结构不变

唯一需要确认的是 `showConfig` 函数中的技能路径解析是否能正确处理新的 `/root/.openclaw/skills/` 路径。

## 迁移策略

### 现有实例处理

对于已经创建的实例，采用**渐进式迁移**策略：

1. **不自动迁移** - 现有实例继续使用旧的 `presets/` 结构
2. **手动触发迁移** - 通过管理接口手动触发迁移
3. **迁移操作**：
   - 将 `presets/identities/{id}/*` 移动到 `workspace/`
   - 将 `presets/skills/{id}` 移动到 `skills/`
   - 更新 docker-compose.yml 中的挂载点
   - 重启容器

### 迁移脚本

```python
async def migrate_instance(name: str):
    """迁移现有实例到新结构"""
    instance_dir = CONFIG_INSTANCES_DIR / name
    
    # 1. 迁移身份文件
    presets_identity = instance_dir / "presets" / "identities"
    if presets_identity.exists():
        for f in presets_identity.rglob("*"):
            if f.is_file():
                rel_path = f.relative_to(presets_identity)
                dst = instance_dir / "workspace" / rel_path.name
                shutil.copy2(f, dst)
    
    # 2. 迁移技能文件
    presets_skills = instance_dir / "presets" / "skills"
    if presets_skills.exists():
        for skill_dir in presets_skills.iterdir():
            if skill_dir.is_dir():
                dst = instance_dir / "skills" / skill_dir.name
                shutil.copytree(skill_dir, dst, dirs_exist_ok=True)
    
    # 3. 创建 identity 目录
    identity_dir = instance_dir / "identity"
    identity_dir.mkdir(exist_ok=True)
```

### 新实例

新创建的实例自动使用新结构，无需额外操作。

## 依赖变更

- 无需新增依赖
- 后端 Python 代码修改，使用标准库 `shutil`, `Path`
- 前端无需修改

## 变更文件清单

| 文件 | 变更类型 | 描述 |
|------|----------|------|
| `est-admin/backend/main.py` | 修改 | 更新实例创建逻辑、挂载配置、技能路径 |
| `docker-compose.yml` | 自动生成 | 由后端代码修改后自动更新 |
| 现有实例配置目录 | 手动迁移 | 需要运行迁移脚本 |

## 测试要点

1. **新实例创建** - 验证新结构正确生成
2. **技能加载** - 验证 `/root/.openclaw/skills/` 下的技能能被正确加载
3. **身份加载** - 验证 `workspace/` 下的身份文件被正确读取
4. **容器启动** - 验证新挂载点下容器能正常启动
5. **现有实例迁移** - 验证迁移脚本正确处理旧结构
