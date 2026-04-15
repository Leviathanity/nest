# Nest Admin 实例管理扩展实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩展 nest-admin 实现多 OpenClaw 实例的完整生命周期管理，包括预制技能仓库、插件仓库、身份模板、模型 Key 集中管理。

**Architecture:** 在现有 nest-admin 基础上新增 presets 目录存储预制内容，扩展 API 实现 preset 管理，新增实例完整目录结构生成逻辑。

**Tech Stack:** Python (FastAPI), Docker SDK, 文件系统操作

---

## 文件结构

```
nest-admin/
├── configs/
│   ├── presets/                    # 新增：预制内容
│   │   ├── keys.json
│   │   ├── skills/
│   │   ├── plugins/
│   │   └── identities/
│   │       ├── employee/
│   │       └── manager/
│   └── instances/
├── backend/
│   └── main.py                     # 扩展：新增 preset API、扩展创建流程
└── frontend/
    └── index.html                  # 扩展：创建表单

configs/base/                        # 现有基础配置
```

---

## Task 1: 创建 Preset 目录结构和示例文件

**Files:**
- Create: `nest-admin/configs/presets/keys.json`
- Create: `nest-admin/configs/presets/skills/github/SKILL.md`
- Create: `nest-admin/configs/presets/identities/employee/SOUL.md`
- Create: `nest-admin/configs/presets/identities/employee/USER.md`
- Create: `nest-admin/configs/presets/identities/employee/IDENTITY.md`
- Create: `nest-admin/configs/presets/identities/employee/HEARTBEAT.md`
- Create: `nest-admin/configs/presets/identities/manager/SOUL.md`
- Create: `nest-admin/configs/presets/identities/manager/USER.md`
- Create: `nest-admin/configs/presets/identities/manager/IDENTITY.md`
- Create: `nest-admin/configs/presets/identities/manager/HEARTBEAT.md`

- [ ] **Step 1: 创建 presets 目录**

```bash
mkdir -p nest-admin/configs/presets/skills/github
mkdir -p nest-admin/configs/presets/identities/employee
mkdir -p nest-admin/configs/presets/identities/manager
```

- [ ] **Step 2: 创建 keys.json**

```json
{
  "version": 1,
  "keys": {
    "minimax": {
      "apiKey": "",
      "label": "MiniMax 主账号"
    },
    "feishu": {
      "appId": "",
      "appSecret": "",
      "verificationToken": "",
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

- [ ] **Step 3: 创建示例技能 SKILL.md (github)**

```markdown
---
name: github
description: GitHub API integration for repository management
---

# GitHub Skill

Use GitHub API for repository management, issue tracking, and code operations.
```

- [ ] **Step 4: 创建 employee 身份模板文件**

`SOUL.md`:
```markdown
# Employee Soul

I am a helpful assistant working as an employee. I focus on efficiency, teamwork, and getting tasks done properly.
```

`USER.md`:
```markdown
# User

Employee Assistant - Your work companion.
```

`IDENTITY.md`:
```markdown
# Identity

You are an AI assistant configured as an employee helper.
```

`HEARTBEAT.md`:
```markdown
# Heartbeat

Perform daily standup reminders and task follow-ups.
```

- [ ] **Step 5: 创建 manager 身份模板文件**

类似 employee，但内容调整为管理者视角。

- [ ] **Step 6: 提交**

```bash
git add nest-admin/configs/presets/
git commit -m "feat: add preset directory structure and sample files"
```

---

## Task 2: 扩展 main.py - Preset Keys 管理 API

**Files:**
- Modify: `nest-admin/backend/main.py`

- [ ] **Step 1: 在 main.py 顶部添加常量**

```python
PRESETS_DIR = Path(os.environ.get("PRESETS_DIR", "/app/configs/presets"))
PRESETS_KEYS_FILE = PRESETS_DIR / "keys.json"
```

- [ ] **Step 2: 添加 Keys 读取辅助函数**

```python
def load_preset_keys() -> dict:
    if PRESETS_KEYS_FILE.exists():
        return json.loads(PRESETS_KEYS_FILE.read_text())
    return {"version": 1, "keys": {}, "defaultProvider": "minimax"}

def save_preset_keys(data: dict):
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    PRESETS_KEYS_FILE.write_text(json.dumps(data, indent=2))
```

- [ ] **Step 3: 添加 Keys API 端点**

在 `@app.get("/api/presets/channels")` 附近添加：

```python
@app.get("/api/presets/keys")
async def get_preset_keys():
    """获取预制 Keys（脱敏显示）"""
    keys_data = load_preset_keys()
    sanitized = {}
    for provider, key_info in keys_data.get("keys", {}).items():
        sanitized[provider] = {
            **key_info,
            "apiKey": mask_key(key_info.get("apiKey", "")),
            "appSecret": mask_key(key_info.get("appSecret", "")),
            "corpSecret": mask_key(key_info.get("corpSecret", ""))
        }
    return {
        **keys_data,
        "keys": sanitized
    }

def mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return "****"
    return key[:4] + "****" + key[-4]

@app.put("/api/presets/keys")
async def update_preset_keys(data: dict):
    """更新预制 Keys"""
    save_preset_keys(data)
    return {"status": "saved"}
```

- [ ] **Step 4: 提交**

```bash
git add nest-admin/backend/main.py
git commit -m "feat: add preset keys management API"
```

---

## Task 3: 扩展 main.py - Identity 和 Skill Preset API

**Files:**
- Modify: `nest-admin/backend/main.py`

- [ ] **Step 1: 添加 Identity 列表 API**

```python
@app.get("/api/presets/identities")
async def list_identities():
    """获取身份模板列表"""
    identities_dir = PRESETS_DIR / "identities"
    if not identities_dir.exists():
        return []
    result = []
    for d in identities_dir.iterdir():
        if d.is_dir():
            result.append({
                "id": d.name,
                "name": d.name.capitalize(),
                "description": f"{d.name} identity template"
            })
    return result

@app.get("/api/presets/identities/{identity_id}")
async def get_identity(identity_id: str):
    """获取身份模板详情"""
    identity_dir = PRESETS_DIR / "identities" / identity_id
    if not identity_dir.exists():
        raise HTTPException(404, f"Identity {identity_id} not found")
    files = {}
    for fname in ["SOUL.md", "USER.md", "IDENTITY.md", "HEARTBEAT.md"]:
        fpath = identity_dir / fname
        if fpath.exists():
            files[fname] = fpath.read_text(encoding="utf-8")
    return {"id": identity_id, "files": files}
```

- [ ] **Step 2: 添加 Skills 列表 API**

```python
@app.get("/api/presets/skills")
async def list_skills():
    """获取技能列表"""
    skills_dir = PRESETS_DIR / "skills"
    if not skills_dir.exists():
        return []
    result = []
    for d in skills_dir.iterdir():
        if d.is_dir():
            skill_md = d / "SKILL.md"
            description = ""
            if skill_md.exists():
                content = skill_md.read_text(encoding="utf-8")
                for line in content.split("\n"):
                    if line.startswith("description:"):
                        description = line.replace("description:", "").strip()
                        break
            result.append({
                "id": d.name,
                "name": d.name,
                "description": description or f"{d.name} skill"
            })
    return result

@app.get("/api/presets/skills/{skill_id}")
async def get_skill(skill_id: str):
    """获取技能详情"""
    skill_dir = PRESETS_DIR / "skills" / skill_id
    if not skill_dir.exists():
        raise HTTPException(404, f"Skill {skill_id} not found")
    skill_md = skill_dir / "SKILL.md"
    content = ""
    if skill_md.exists():
        content = skill_md.read_text(encoding="utf-8")
    return {"id": skill_id, "content": content}
```

- [ ] **Step 3: 添加 Plugins 列表 API**

```python
@app.get("/api/presets/plugins")
async def list_plugins():
    """获取插件列表"""
    plugins_dir = PRESETS_DIR / "plugins"
    if not plugins_dir.exists():
        return []
    result = []
    for d in plugins_dir.iterdir():
        if d.is_dir():
            result.append({
                "id": d.name,
                "name": d.name,
                "description": f"{d.name} plugin"
            })
    return result
```

- [ ] **Step 4: 提交**

```bash
git add nest-admin/backend/main.py
git commit -m "feat: add identity and skill preset APIs"
```

---

## Task 4: 扩展 main.py - 增强实例创建流程

**Files:**
- Modify: `nest-admin/backend/main.py`

- [ ] **Step 1: 添加文件复制辅助函数**

```python
def copy_directory(src: Path, dst: Path, files: list = None):
    """复制目录，可选只复制指定文件列表"""
    dst.mkdir(parents=True, exist_ok=True)
    if files is None:
        files = [f.name for f in src.iterdir() if f.is_file()]
    for fname in files:
        src_file = src / fname
        if src_file.exists():
            dst_file = dst / fname
            dst_file.write_text(src_file.read_text(encoding="utf-8"), encoding="utf-8")

def apply_identity_to_instance(instance_dir: Path, identity_id: str):
    """应用身份模板到实例"""
    identity_dir = PRESETS_DIR / "identities" / identity_id
    if not identity_dir.exists():
        return
    workspace_dir = instance_dir / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    for fname in ["SOUL.md", "USER.md", "IDENTITY.md", "HEARTBEAT.md"]:
        src_file = identity_dir / fname
        if src_file.exists():
            dst_file = workspace_dir / fname
            dst_file.write_text(src_file.read_text(encoding="utf-8"), encoding="utf-8")

def apply_skills_to_instance(instance_dir: Path, skill_ids: list):
    """应用技能到实例"""
    skills_dir = instance_dir / "workspace" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    for skill_id in skill_ids:
        src_dir = PRESETS_DIR / "skills" / skill_id
        if src_dir.exists():
            dst_dir = skills_dir / skill_id
            dst_dir.mkdir(parents=True, exist_ok=True)
            for f in src_dir.iterdir():
                if f.is_file():
                    (dst_dir / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")

def apply_plugins_to_instance(instance_dir: Path, plugin_ids: list, keys_data: dict):
    """应用插件到实例"""
    plugins_dir = instance_dir / "skills"
    extensions_dir = instance_dir / "extensions"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    extensions_dir.mkdir(parents=True, exist_ok=True)
    for plugin_id in plugin_ids:
        src_dir = PRESETS_DIR / "plugins" / plugin_id
        if src_dir.exists():
            dst_dir = plugins_dir / plugin_id
            dst_dir.mkdir(parents=True, exist_ok=True)
            for f in src_dir.iterdir():
                if f.is_file():
                    (dst_dir / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
```

- [ ] **Step 2: 扩展 create_instance 请求模型**

```python
class InstanceCreateRequest(BaseModel):
    name: str
    image: Optional[str] = "openclaw:pure-gpu"
    identity: Optional[str] = "empty"
    skills: Optional[list[str]] = []
    plugins: Optional[list[str]] = []
    modelProvider: Optional[str] = "minimax"
    channels: Optional[dict] = {}
```

- [ ] **Step 3: 重构 create_instance 函数**

修改 `@app.post("/api/instances")` 处理完整创建流程：

```python
@app.post("/api/instances")
async def create_instance(data: InstanceCreateRequest):
    name = data.name
    # 验证名称
    if not isinstance(name, str) or not name.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(400, "name must be alphanumeric with dashes/underscores only")
    instance_dir = CONFIG_INSTANCES_DIR / name
    if instance_dir.exists():
        raise HTTPException(400, f"Instance {name} already exists")

    instance_id = get_next_instance_id()
    instance_dir.mkdir(parents=True, exist_ok=True)

    # 生成 token
    token = secrets.token_hex(16)

    # 加载预制 Keys
    keys_data = load_preset_keys()

    # 构建 openclaw.json 配置
    config = build_instance_config(instance_id, name, token, data, keys_data)
    (instance_dir / "openclaw.json").write_text(json.dumps(config, indent=2))

    # 创建目录结构
    create_instance_directories(instance_dir)

    # 应用身份模板
    if data.identity and data.identity != "empty":
        apply_identity_to_instance(instance_dir, data.identity)

    # 应用技能
    if data.skills:
        apply_skills_to_instance(instance_dir, data.skills)

    # 应用插件
    if data.plugins:
        apply_plugins_to_instance(instance_dir, data.plugins, keys_data)

    return {"name": name, "instance_id": instance_id, "status": "created"}

def build_instance_config(instance_id: int, name: str, token: str, data: InstanceCreateRequest, keys_data: dict) -> dict:
    """构建实例的 openclaw.json"""
    config = {
        "cluster": {
            "instanceId": instance_id,
            "instanceName": name,
            "description": f"Instance {name}"
        },
        "gateway": {
            "mode": "local",
            "bind": "lan",
            "controlUi": {
                "dangerouslyDisableDeviceAuth": True,
                "allowInsecureAuth": True
            },
            "auth": {
                "mode": "token",
                "token": token
            }
        },
        "logging": {
            "level": "info"
        }
    }

    # 添加模型配置
    model_provider = data.modelProvider or keys_data.get("defaultProvider", "minimax")
    if model_provider in keys_data.get("keys", {}):
        provider_keys = keys_data["keys"][model_provider]
        if "apiKey" in provider_keys:
            config["env"] = {"MINIMAX_API_KEY": provider_keys["apiKey"]}

    # 添加渠道配置
    if data.channels:
        config["channels"] = {}
        if data.channels.get("feishu"):
            feishu_keys = keys_data.get("keys", {}).get("feishu", {})
            if feishu_keys.get("appId"):
                config["channels"]["feishu"] = {
                    "enabled": True,
                    "appId": feishu_keys.get("appId"),
                    "appSecret": feishu_keys.get("appSecret"),
                    "verificationToken": feishu_keys.get("verificationToken"),
                    "dmPolicy": "open",
                    "allowFrom": ["*"]
                }
        if data.channels.get("weixin"):
            config["channels"]["weixin"] = {"enabled": True}

    # 添加插件配置
    if data.plugins:
        config["plugins"] = {
            "allow": data.plugins,
            "load": {"paths": ["/app/extensions", "/root/.openclaw/extensions"]}
        }

    return config

def create_instance_directories(instance_dir: Path):
    """创建实例完整目录结构"""
    dirs = [
        "agents/main/agent",
        "workspace/skills",
        "workspace/memory",
        "skills",
        "extensions",
        "memory",
        "browser/profiles",
        "cron",
        "logs",
        "devices",
        "canvas",
        "delivery-queue",
        "local"
    ]
    for d in dirs:
        (instance_dir / d).mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: 提交**

```bash
git add nest-admin/backend/main.py
git commit -m "feat: enhance instance creation with preset support"
```

---

## Task 5: 更新前端创建表单

**Files:**
- Modify: `nest-admin/frontend/index.html`

- [ ] **Step 1: 添加预设数据获取**

在 JavaScript 中添加：

```javascript
async function loadPresets() {
    const [identities, skills, plugins, keys, providers] = await Promise.all([
        fetch('/api/presets/identities').then(r => r.json()),
        fetch('/api/presets/skills').then(r => r.json()),
        fetch('/api/presets/plugins').then(r => r.json()),
        fetch('/api/presets/keys').then(r => r.json()),
        fetch('/api/presets/model-providers').then(r => r.json())
    ]);
    return { identities, skills, plugins, keys, providers };
}
```

- [ ] **Step 2: 扩展创建表单 UI**

在现有表单中添加：

```html
<div class="form-group">
    <label>身份模板</label>
    <select id="instance-identity">
        <option value="empty">空白</option>
        <option value="employee">员工助手</option>
        <option value="manager">管理者</option>
    </select>
</div>

<div class="form-group">
    <label>预置技能</label>
    <div id="skills-checkboxes"></div>
</div>

<div class="form-group">
    <label>预置插件</label>
    <div>
        <label><input type="checkbox" id="plugin-feishu"> 飞书</label>
        <label><input type="checkbox" id="plugin-weixin"> 企业微信 (二维码配对)</label>
    </div>
</div>

<div class="form-group">
    <label>模型提供商</label>
    <select id="model-provider"></select>
</div>

<div class="form-group">
    <label>渠道配置</label>
    <div>
        <label><input type="checkbox" id="channel-feishu"> 启用飞书</label>
        <label><input type="checkbox" id="channel-weixin"> 启用微信</label>
    </div>
</div>
```

- [ ] **Step 3: 修改创建请求逻辑**

```javascript
async function createInstance() {
    const name = document.getElementById('instance-name').value;
    const image = document.querySelector('input[name="image"]:checked').value;
    const identity = document.getElementById('instance-identity').value;

    const skills = [];
    document.querySelectorAll('#skills-checkboxes input:checked').forEach(cb => {
        skills.push(cb.value);
    });

    const plugins = [];
    if (document.getElementById('plugin-feishu').checked) plugins.push('feishu');
    if (document.getElementById('plugin-weixin').checked) plugins.push('openclaw-weixin');

    const channels = {};
    if (document.getElementById('channel-feishu').checked) channels.feishu = true;
    if (document.getElementById('channel-weixin').checked) channels.weixin = true;

    const response = await fetch('/api/instances', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name, image, identity, skills, plugins,
            modelProvider: 'minimax', channels
        })
    });
    // handle response...
}
```

- [ ] **Step 4: 提交**

```bash
git add nest-admin/frontend/index.html
git commit -m "feat: extend frontend with preset selection UI"
```

---

## Task 6: 添加预设管理页面

**Files:**
- Modify: `nest-admin/frontend/index.html`

- [ ] **Step 1: 添加 Keys 管理 Tab**

```html
<div class="tab-content" id="tab-keys">
    <h3>预制 Keys 管理</h3>
    <form id="keys-form">
        <div class="form-group">
            <label>MiniMax API Key</label>
            <input type="password" id="key-minimax-apikey" placeholder="sk-...">
        </div>
        <div class="form-group">
            <label>飞书 App ID</label>
            <input type="text" id="key-feishu-appid" placeholder="cli_...">
        </div>
        <div class="form-group">
            <label>飞书 App Secret</label>
            <input type="password" id="key-feishu-appsecret">
        </div>
        <button type="submit">保存</button>
    </form>
</div>
```

- [ ] **Step 2: 添加保存 Keys 逻辑**

```javascript
document.getElementById('keys-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    await fetch('/api/presets/keys', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            version: 1,
            keys: {
                minimax: { apiKey: document.getElementById('key-minimax-apikey').value, label: "MiniMax" },
                feishu: {
                    appId: document.getElementById('key-feishu-appid').value,
                    appSecret: document.getElementById('key-feishu-appsecret').value,
                    label: "飞书"
                }
            },
            defaultProvider: "minimax"
        })
    });
    alert('已保存');
});
```

- [ ] **Step 3: 提交**

```bash
git add nest-admin/frontend/index.html
git commit -m "feat: add preset keys management UI"
```

---

## 实现检查清单

- [ ] Task 1: Preset 目录结构和示例文件
- [ ] Task 2: Keys 管理 API
- [ ] Task 3: Identity 和 Skill Preset API
- [ ] Task 4: 增强实例创建流程
- [ ] Task 5: 前端创建表单扩展
- [ ] Task 6: 预设 Keys 管理页面

---

## 执行选项

**Plan complete and saved to `docs/superpowers/plans/2026-04-15-nest-admin-instance-management-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
