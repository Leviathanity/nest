# Nest Admin 创建实例界面重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构 Nest Admin 创建实例界面，采用标签页分组展示预设资源（身份模板、技能、插件），每项以详细信息卡片呈现。

**Architecture:** 保持现有后端 API 不变，新增前端创建实例弹窗的 UI 组件，采用标签页分组、卡片网格布局，支持搜索和已选项目管理。

**Tech Stack:** 纯 HTML/CSS/JS，无需新框架

---

## 文件结构

```
nest-admin/
├── frontend/
│   └── index.html     # 修改：重构创建实例弹窗 UI
└── backend/
    └── main.py        # 可能需要：新增获取预设详情的 API（如文件列表）
```

---

## 任务分解

### Task 1: 重构创建实例弹窗 HTML 结构

**Files:**
- Modify: `nest-admin/frontend/index.html:277-324`

- [ ] **Step 1: 读取当前创建实例弹窗代码**

确认 `modal-create` 弹窗的当前实现（行 277-324）

- [ ] **Step 2: 替换为新的标签页结构**

```html
<!-- Create Instance Modal -->
<div id="modal-create" class="modal">
    <div class="modal-content" style="max-width:900px;">
        <div class="modal-header">
            <h3>创建新实例</h3>
            <button class="modal-close" onclick="closeModal('create')">&times;</button>
        </div>
        
        <!-- 标签页切换 -->
        <div class="create-tabs">
            <button class="create-tab active" data-create-tab="identity">身份模板</button>
            <button class="create-tab" data-create-tab="skills">技能</button>
            <button class="create-tab" data-create-tab="plugins">插件</button>
        </div>
        
        <!-- 搜索栏 -->
        <div class="create-search-bar">
            <input type="text" id="create-search" placeholder="搜索..." oninput="filterCreateItems()">
            <span id="selected-count">已选: 0项</span>
            <button onclick="clearCreateSelections()">清空</button>
        </div>
        
        <!-- 标签页内容 -->
        <div class="create-tab-content">
            <!-- 身份模板 -->
            <div id="create-tab-identity" class="create-tab-panel active">
                <div id="identity-cards" class="preset-cards-grid"></div>
            </div>
            
            <!-- 技能 -->
            <div id="create-tab-skills" class="create-tab-panel" style="display:none;">
                <div id="skills-cards" class="preset-cards-grid"></div>
            </div>
            
            <!-- 插件 -->
            <div id="create-tab-plugins" class="create-tab-panel" style="display:none;">
                <div id="plugins-cards" class="preset-cards-grid"></div>
            </div>
        </div>
        
        <!-- 已选项目区域 -->
        <div class="selected-items-section">
            <div class="section-title">已选项目</div>
            <div id="selected-items-list" class="selected-items-list"></div>
        </div>
        
        <!-- 底部表单 -->
        <div class="create-form-footer">
            <div class="form-group">
                <label>实例名称</label>
                <input type="text" id="instance-name" placeholder="my-openclaw">
            </div>
            <div class="form-group">
                <label>镜像类型</label>
                <div>
                    <label><input type="radio" name="image" value="openclaw:pure-gpu" checked> GPU</label>
                    <label><input type="radio" name="image" value="openclaw:pure-cpu"> CPU</label>
                </div>
            </div>
        </div>
        
        <div class="modal-footer">
            <button onclick="closeModal('create')">取消</button>
            <button class="primary" onclick="createInstance()">创建实例</button>
        </div>
    </div>
</div>
```

- [ ] **Step 3: 添加新的 CSS 样式**

在 `<style>` 标签内添加：

```css
/* Create Instance Modal Styles */
.create-tabs { display: flex; gap: 4px; background: #f0f0f0; padding: 4px; border-radius: 6px; margin-bottom: 16px; }
.create-tab { padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; border: none; background: transparent; }
.create-tab.active { background: #fff; box-shadow: 0 1px 2px rgba(0,0,0,0.1); color: #1890ff; border-bottom: 3px solid #1890ff; }
.create-tab:hover:not(.active) { background: #e6e6e6; }

.create-search-bar { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
.create-search-bar input { flex: 1; padding: 8px 12px; border: 1px solid #d9d9d9; border-radius: 4px; font-size: 14px; }
.create-search-bar span { font-size: 13px; color: #666; }
.create-search-bar button { padding: 6px 12px; border-radius: 4px; border: 1px solid #d9d9d9; cursor: pointer; font-size: 13px; background: #fff; }
.create-search-bar button:hover { border-color: #1890ff; color: #1890ff; }

.preset-cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; max-height: 320px; overflow-y: auto; padding: 4px; }

.preset-card { background: #fff; border: 1px solid #e8e8e8; border-radius: 6px; padding: 16px; cursor: pointer; transition: all 0.2s; }
.preset-card:hover { border-color: #1890ff; box-shadow: 0 2px 8px rgba(24,144,255,0.15); }
.preset-card.selected { border-color: #1890ff; background: #e6f7ff; }
.preset-card.selected::after { content: '✓'; position: absolute; top: 8px; right: 8px; width: 20px; height: 20px; background: #1890ff; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; }

.preset-card-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.preset-card-radio { width: 16px; height: 16px; }
.preset-card-name { font-weight: 600; font-size: 14px; }
.preset-card-desc { font-size: 12px; color: #666; margin-bottom: 8px; }
.preset-card-files { font-size: 11px; color: #999; }
.preset-card-files strong { color: #666; }

.selected-items-section { background: #fafafa; border-radius: 6px; padding: 12px; margin: 16px 0; }
.selected-items-section .section-title { font-size: 13px; font-weight: 600; color: #333; margin-bottom: 8px; }
.selected-items-list { display: flex; flex-wrap: wrap; gap: 8px; }
.selected-item { display: inline-flex; align-items: center; gap: 6px; padding: 4px 8px; background: #e6f7ff; color: #1890ff; border-radius: 4px; font-size: 12px; }
.selected-item button { background: none; border: none; cursor: pointer; color: #1890ff; padding: 0; font-size: 14px; line-height: 1; }
.selected-item button:hover { color: #ff4d4f; }

.create-form-footer { display: flex; gap: 16px; align-items: flex-end; margin-top: 16px; padding-top: 16px; border-top: 1px solid #f0f0f0; }
.create-form-footer .form-group { flex: 1; margin-bottom: 0; }
.create-form-footer .form-group label { display: block; margin-bottom: 4px; font-size: 13px; color: #666; font-weight: 500; }
```

- [ ] **Step 4: 提交**

```bash
git add nest-admin/frontend/index.html
git commit -m "feat(frontend): add create instance modal HTML structure and CSS"
```

---

### Task 2: 实现创建实例弹窗的 JavaScript 逻辑

**Files:**
- Modify: `nest-admin/frontend/index.html:700-760` (showCreateModal 函数附近)

- [ ] **Step 1: 添加创建实例相关状态变量**

在 `let currentWorkspaceFile = null;` 后添加：

```javascript
let createSelections = {
    identity: null,
    skills: [],
    plugins: []
};
let currentCreateTab = 'identity';
```

- [ ] **Step 2: 修改 showCreateModal 函数**

找到现有 `showCreateModal` 函数（约行 687-709），替换为：

```javascript
function showCreateModal() {
    document.getElementById('instance-name').value = '';
    document.querySelectorAll('input[name="image"]')[0].checked = true;
    
    // 重置选择状态
    createSelections = { identity: null, skills: [], plugins: [] };
    currentCreateTab = 'identity';
    
    // 渲染各标签页卡片
    renderIdentityCards();
    renderSkillsCards();
    renderPluginsCards();
    
    // 设置标签页
    document.querySelectorAll('.create-tab').forEach(t => t.classList.remove('active'));
    document.querySelector('.create-tab').classList.add('active');
    document.querySelectorAll('.create-tab-panel').forEach(p => p.style.display = 'none');
    document.getElementById('create-tab-identity').style.display = 'block';
    
    // 更新已选显示
    updateSelectedItemsDisplay();
    
    document.getElementById('modal-create').classList.add('show');
}
```

- [ ] **Step 3: 添加渲染函数**

在 `renderSkillsCheckboxesCreate` 函数后添加：

```javascript
function renderIdentityCards() {
    const container = document.getElementById('identity-cards');
    const searchTerm = document.getElementById('create-search').value.toLowerCase();
    const filtered = (presets.identities || []).filter(id => 
        id.name.toLowerCase().includes(searchTerm) || 
        (id.description || '').toLowerCase().includes(searchTerm)
    );
    
    if (!filtered.length) {
        container.innerHTML = '<div class="empty-state">暂无身份模板</div>';
        return;
    }
    
    container.innerHTML = filtered.map(id => {
        const isSelected = createSelections.identity === id.id;
        const files = ['SOUL.md', 'USER.md', 'IDENTITY.md', 'HEARTBEAT.md'];
        return `
        <div class="preset-card ${isSelected ? 'selected' : ''}" onclick="toggleIdentitySelection('${id.id}')">
            <div class="preset-card-header">
                <input type="radio" class="preset-card-radio" name="identity" value="${id.id}" ${isSelected ? 'checked' : ''}>
                <span class="preset-card-name">${id.name}</span>
            </div>
            <div class="preset-card-desc">${id.description || '无描述'}</div>
            <div class="preset-card-files"><strong>文件:</strong> ${files.join(', ')}</div>
        </div>
    `}).join('');
}

function renderSkillsCards() {
    const container = document.getElementById('skills-cards');
    const searchTerm = document.getElementById('create-search').value.toLowerCase();
    const filtered = (presets.skills || []).filter(s => 
        s.name.toLowerCase().includes(searchTerm) || 
        (s.description || '').toLowerCase().includes(searchTerm)
    );
    
    if (!filtered.length) {
        container.innerHTML = '<div class="empty-state">暂无技能</div>';
        return;
    }
    
    container.innerHTML = filtered.map(skill => {
        const isSelected = createSelections.skills.includes(skill.id);
        return `
        <div class="preset-card ${isSelected ? 'selected' : ''}" onclick="toggleSkillSelection('${skill.id}')">
            <div class="preset-card-header">
                <input type="checkbox" class="preset-card-radio" ${isSelected ? 'checked' : ''}>
                <span class="preset-card-name">${skill.name}</span>
            </div>
            <div class="preset-card-desc">${skill.description || '无描述'}</div>
            <div class="preset-card-files"><strong>文件:</strong> SKILL.md</div>
        </div>
    `}).join('');
}

function renderPluginsCards() {
    const container = document.getElementById('plugins-cards');
    const searchTerm = document.getElementById('create-search').value.toLowerCase();
    const filtered = (presets.plugins || []).filter(p => 
        p.name.toLowerCase().includes(searchTerm) || 
        (p.description || '').toLowerCase().includes(searchTerm)
    );
    
    if (!filtered.length) {
        container.innerHTML = '<div class="empty-state">暂无插件</div>';
        return;
    }
    
    container.innerHTML = filtered.map(plugin => {
        const isSelected = createSelections.plugins.includes(plugin.id);
        return `
        <div class="preset-card ${isSelected ? 'selected' : ''}" onclick="togglePluginSelection('${plugin.id}')">
            <div class="preset-card-header">
                <input type="checkbox" class="preset-card-radio" ${isSelected ? 'checked' : ''}>
                <span class="preset-card-name">${plugin.name}</span>
            </div>
            <div class="preset-card-desc">${plugin.description || '无描述'}</div>
        </div>
    `}).join('');
}

function toggleIdentitySelection(id) {
    createSelections.identity = createSelections.identity === id ? null : id;
    renderIdentityCards();
    updateSelectedItemsDisplay();
}

function toggleSkillSelection(id) {
    const idx = createSelections.skills.indexOf(id);
    if (idx >= 0) {
        createSelections.skills.splice(idx, 1);
    } else {
        createSelections.skills.push(id);
    }
    renderSkillsCards();
    updateSelectedItemsDisplay();
}

function togglePluginSelection(id) {
    const idx = createSelections.plugins.indexOf(id);
    if (idx >= 0) {
        createSelections.plugins.splice(idx, 1);
    } else {
        createSelections.plugins.push(id);
    }
    renderPluginsCards();
    updateSelectedItemsDisplay();
}

function updateSelectedItemsDisplay() {
    const container = document.getElementById('selected-items-list');
    const countSpan = document.getElementById('selected-count');
    const items = [];
    
    if (createSelections.identity) {
        const id = presets.identities.find(i => i.id === createSelections.identity);
        if (id) items.push(`<span class="selected-item">${id.name} <button onclick="event.stopPropagation();toggleIdentitySelection('${id.id}')">×</button></span>`);
    }
    
    createSelections.skills.forEach(sid => {
        const skill = presets.skills.find(s => s.id === sid);
        if (skill) items.push(`<span class="selected-item">${skill.name} <button onclick="event.stopPropagation();toggleSkillSelection('${sid}')">×</button></span>`);
    });
    
    createSelections.plugins.forEach(pid => {
        const plugin = presets.plugins.find(p => p.id === pid);
        if (plugin) items.push(`<span class="selected-item">${plugin.name} <button onclick="event.stopPropagation();togglePluginSelection('${pid}')">×</button></span>`);
    });
    
    container.innerHTML = items.length ? items.join('') : '<span style="color:#999;font-size:12px;">未选择任何项目</span>';
    countSpan.textContent = `已选: ${items.length}项`;
}

function clearCreateSelections() {
    createSelections = { identity: null, skills: [], plugins: [] };
    if (currentCreateTab === 'identity') renderIdentityCards();
    else if (currentCreateTab === 'skills') renderSkillsCards();
    else renderPluginsCards();
    updateSelectedItemsDisplay();
}

function filterCreateItems() {
    if (currentCreateTab === 'identity') renderIdentityCards();
    else if (currentCreateTab === 'skills') renderSkillsCards();
    else renderPluginsCards();
}
```

- [ ] **Step 4: 添加标签页切换逻辑**

找到 `showCreateModal` 调用附近，添加标签页切换事件监听：

在 `<script>` 标签末尾添加 DOMContentLoaded 事件处理（如果还没有）：

```javascript
document.addEventListener('DOMContentLoaded', function() {
    // 现有的其他初始化代码...

    // 创建实例标签页切换
    document.querySelectorAll('.create-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.dataset.createTab;
            currentCreateTab = tabName;
            document.querySelectorAll('.create-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            document.querySelectorAll('.create-tab-panel').forEach(p => p.style.display = 'none');
            document.getElementById('create-tab-' + tabName).style.display = 'block';
            // 清空搜索
            document.getElementById('create-search').value = '';
            filterCreateItems();
        });
    });
});
```

- [ ] **Step 5: 修改 createInstance 函数**

找到现有 `createInstance` 函数（约行 725-753），替换为：

```javascript
async function createInstance() {
    const name = document.getElementById('instance-name').value.trim();
    if (!name) { showAlert('error', '请输入实例名称'); return; }
    if (!createSelections.identity) { showAlert('error', '请选择身份模板'); return; }
    
    const image = document.querySelector('input[name="image"]:checked').value;

    try {
        await api('POST', '/api/instances', {
            name,
            image,
            identity: createSelections.identity,
            skills: createSelections.skills,
            plugins: createSelections.plugins,
            modelProvider: 'minimax',
            channels: {}
        });
        closeModal('create');
        showAlert('success', `${name} 创建成功`);
        setTimeout(loadInstances, 1000);
    } catch (e) { showAlert('error', e.message); }
}
```

- [ ] **Step 6: 提交**

```bash
git add nest-admin/frontend/index.html
git commit -m "feat(frontend): implement create instance modal JS logic"
```

---

### Task 3: 测试创建实例功能

- [ ] **Step 1: 在浏览器中打开 nest-admin**

访问 http://192.168.2.118:3000 （或对应的地址）

- [ ] **Step 2: 测试创建实例弹窗**

1. 点击"创建实例"按钮
2. 验证弹窗显示三个标签页：身份模板、技能、插件
3. 切换标签页，验证内容正确切换
4. 测试搜索功能
5. 选择一个身份模板、一个技能、一个插件
6. 验证已选项目区域正确显示
7. 测试移除单个已选项
8. 测试清空按钮

- [ ] **Step 3: 测试创建流程**

1. 输入实例名称
2. 选择 GPU/CPU
3. 点击"创建实例"
4. 验证实例创建成功并出现在列表中

- [ ] **Step 4: 提交**

```bash
git add nest-admin/frontend/index.html
git commit -m "test(frontend): verify create instance modal functionality"
```

---

## 实施检查清单

- [ ] Task 1: HTML 结构与 CSS 完成
- [ ] Task 2: JavaScript 逻辑完成
- [ ] Task 3: 功能测试通过
- [ ] 所有修改已提交
