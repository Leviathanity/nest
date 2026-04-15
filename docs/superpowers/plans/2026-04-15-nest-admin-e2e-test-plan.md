# Nest Admin E2E 测试计划

## 测试目标

验证 nest-admin 实例管理扩展功能是否按设计规范正常工作。

## 测试环境

- Docker Compose 项目: `nest-admin`
- 后端端口: 8080
- 前端端口: 3000
- HTTPS 代理端口: 18443

## 前置条件

1. Docker 和 Docker Compose 已安装
2. `nest_openclaw-net` 网络已创建
3. `.env` 文件配置正确

---

## Test Case 1: 预设 Keys API

### TC1.1 获取预设 Keys (GET /api/presets/keys)

**步骤:**
```bash
curl -s http://localhost:8080/api/presets/keys | python -m json.tool
```

**预期结果:**
- 返回 200 状态码
- JSON 包含 `keys` 对象和 `defaultProvider`
- API Keys 应被脱敏显示 (如 `sk-xxxx...xxxx`)

### TC1.2 更新预设 Keys (PUT /api/presets/keys)

**步骤:**
```bash
curl -s -X PUT http://localhost:8080/api/presets/keys \
  -H "Content-Type: application/json" \
  -d '{
    "version": 1,
    "keys": {
      "minimax": {"apiKey": "test-key-12345678", "label": "Test"},
      "feishu": {"appId": "cli_test", "appSecret": "secret123", "label": "Feishu Test"}
    },
    "defaultProvider": "minimax"
  }'
```

**预期结果:**
- 返回 200 状态码
- 再次 GET 时能看到更新后的值

---

## Test Case 2: 预设 Identity API

### TC2.1 获取 Identity 列表 (GET /api/presets/identities)

**步骤:**
```bash
curl -s http://localhost:8080/api/presets/identities | python -m json.tool
```

**预期结果:**
- 返回 200 状态码
- 包含 `employee` 和 `manager` 两个 identity
- 每个 entry 有 `id`, `name`, `description`

### TC2.2 获取 Identity 详情 (GET /api/presets/identities/{id})

**步骤:**
```bash
curl -s http://localhost:8080/api/presets/identities/employee | python -m json.tool
```

**预期结果:**
- 返回 200 状态码
- 包含 `SOUL.md`, `USER.md`, `IDENTITY.md`, `HEARTBEAT.md` 内容

---

## Test Case 3: 预设 Skills API

### TC3.1 获取 Skills 列表 (GET /api/presets/skills)

**步骤:**
```bash
curl -s http://localhost:8080/api/presets/skills | python -m json.tool
```

**预期结果:**
- 返回 200 状态码
- 包含 `github` skill

### TC3.2 获取 Skill 详情 (GET /api/presets/skills/{id})

**步骤:**
```bash
curl -s http://localhost:8080/api/presets/skills/github | python -m json.tool
```

**预期结果:**
- 返回 200 状态码
- 包含 `id` 和 `content` (SKILL.md 内容)

---

## Test Case 4: 预设 Plugins API

### TC4.1 获取 Plugins 列表 (GET /api/presets/plugins)

**步骤:**
```bash
curl -s http://localhost:8080/api/presets/plugins | python -m json.tool
```

**预期结果:**
- 返回 200 状态码
- 返回插件列表（当前可能为空，因为没有预设插件）

---

## Test Case 5: 实例创建

### TC5.1 创建带预设的实例

**步骤:**
```bash
curl -s -X POST http://localhost:8080/api/instances \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-e2e-instance",
    "image": "openclaw:pure-gpu",
    "identity": "employee",
    "skills": ["github"],
    "plugins": ["feishu"],
    "modelProvider": "minimax",
    "channels": {"feishu": true, "weixin": false}
  }' | python -m json.tool
```

**预期结果:**
- 返回 200 状态码
- 返回 `{"Name": "test-e2e-instance", "instance_id": <id>, "status": "created"}`

### TC5.2 验证实例配置文件生成

**步骤:**
```bash
# 检查容器内
docker exec nest-admin ls -la /app/configs/instances/test-e2e-instance/

# 检查关键文件
docker exec nest-admin cat /app/configs/instances/test-e2e-instance/openclaw.json
```

**预期结果:**
- 目录存在
- `openclaw.json` 包含 cluster, gateway, logging 配置
- 如果 channels 配置正确，应包含 feishu 配置

### TC5.3 验证身份文件复制

**步骤:**
```bash
docker exec nest-admin cat /app/configs/instances/test-e2e-instance/workspace/SOUL.md
```

**预期结果:**
- SOUL.md 存在且内容为 employee 模板内容

### TC5.4 验证技能文件复制

**步骤:**
```bash
docker exec nest-admin cat /app/configs/instances/test-e2e-instance/workspace/skills/github/SKILL.md
```

**预期结果:**
- SKILL.md 存在

---

## Test Case 6: 实例生命周期

### TC6.1 列出实例 (GET /api/instances)

**步骤:**
```bash
curl -s http://localhost:8080/api/instances | python -m json.tool
```

**预期结果:**
- 返回 200 状态码
- 包含 `test-e2e-instance`

### TC6.2 删除实例 (DELETE /api/instances/{name})

**步骤:**
```bash
curl -s -X DELETE http://localhost:8080/api/instances/test-e2e-instance | python -m json.tool
```

**预期结果:**
- 返回 200 状态码
- 实例目录被删除

---

## Test Case 7: 前端 UI

### TC7.1 访问前端

**步骤:**
打开浏览器访问 http://localhost:3000

**预期结果:**
- 页面正常加载
- 显示"实例" tab
- 有"创建实例"按钮

### TC7.2 访问预设 Keys 管理

**步骤:**
在 UI 中点击"预制Keys" tab

**预期结果:**
- 显示 Keys 管理表单
- 有 MiniMax API Key、飞书 App ID、飞书 App Secret 字段

---

## Test Case 8: 错误处理

### TC8.1 创建同名实例（应失败）

**步骤:**
```bash
# 先创建一个实例
curl -s -X POST http://localhost:8080/api/instances \
  -H "Content-Type: application/json" \
  -d '{"name": "duplicate-test", "identity": "employee"}'

# 再次创建同名实例
curl -s -X POST http://localhost:8080/api/instances \
  -H "Content-Type: application/json" \
  -d '{"name": "duplicate-test", "identity": "employee"}' | python -m json.tool
```

**预期结果:**
- 第二次返回错误，实例已存在

### TC8.2 路径遍历防护

**步骤:**
```bash
curl -s http://localhost:8080/api/presets/skills/../../../etc/passwd | python -m json.tool
```

**预期结果:**
- 返回 400 错误或空结果

---

## 执行命令汇总

```bash
# 1. 构建镜像
docker-compose -f nest-admin-compose.yml build

# 2. 启动容器
docker-compose -f nest-admin-compose.yml up -d

# 3. 等待服务就绪
sleep 10

# 4. 执行测试

# TC1.1
curl -s http://localhost:8080/api/presets/keys

# TC1.2
curl -s -X PUT http://localhost:8080/api/presets/keys -H "Content-Type: application/json" -d '{"version":1,"keys":{"minimax":{"apiKey":"test-key-12345678","label":"Test"}},"defaultProvider":"minimax"}'

# TC2.1
curl -s http://localhost:8080/api/presets/identities

# TC2.2
curl -s http://localhost:8080/api/presets/identities/employee

# TC3.1
curl -s http://localhost:8080/api/presets/skills

# TC3.2
curl -s http://localhost:8080/api/presets/skills/github

# TC4.1
curl -s http://localhost:8080/api/presets/plugins

# TC5.1 创建实例
curl -s -X POST http://localhost:8080/api/instances -H "Content-Type: application/json" -d '{"name":"test-e2e-instance","identity":"employee","skills":["github"],"plugins":["feishu"],"channels":{"feishu":true}}'

# TC6.1 列出实例
curl -s http://localhost:8080/api/instances

# TC6.2 删除实例
curl -s -X DELETE http://localhost:8080/api/instances/test-e2e-instance

# 5. 查看日志
docker-compose -f nest-admin-compose.yml logs -f
```

---

## 测试结果记录

| Test Case | Status | Actual Result |
|-----------|--------|---------------|
| TC1.1 GET keys | - | - |
| TC1.2 PUT keys | - | - |
| TC2.1 GET identities | - | - |
| TC2.2 GET identity detail | - | - |
| TC3.1 GET skills | - | - |
| TC3.2 GET skill detail | - | - |
| TC4.1 GET plugins | - | - |
| TC5.1 Create instance | - | - |
| TC5.2 Verify config | - | - |
| TC5.3 Verify identity files | - | - |
| TC5.4 Verify skill files | - | - |
| TC6.1 List instances | - | - |
| TC6.2 Delete instance | - | - |
| TC7.1 Frontend access | - | - |
| TC7.2 Keys UI | - | - |
| TC8.1 Duplicate name | - | - |
| TC8.2 Path traversal | - | - |
