# Direct Mount Volume Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

**Goal:** Change from "copy on start" to "direct mount" pattern - mount instance config directly to `/root/.openclaw` instead of using named volume + copy

**Architecture:** Remove named volume `nest_openclaw-{id}-data` and copy operations. Mount `configs/instances/{name}` directly to `/root/.openclaw` with read-write mode. OpenClaw will read/write config directly from host directory.

**Tech Stack:** Docker SDK, Python, FastAPI

---

## File to Modify

`C:\Users\daemo\workplace\nest\nest-admin\backend\main.py`

### Current Volume Mounts (lines 513-517):
```python
volumes={
    data_volume_name: {"bind": "/root/.openclaw", "mode": "rw"},  # REMOVE
    "C:\\Users\\daemo\\workplace\\nest\\configs\\base": {"bind": "/app/configs/base", "mode": "ro"},
    "C:\\Users\\daemo\\workplace\\nest\\configs\\instances\\" + name: {"bind": "/app/configs/instance", "mode": "ro"},
}
```

### New Volume Mounts:
```python
volumes={
    "C:\\Users\\daemo\\workplace\\nest\\configs\\instances\\" + name: {"bind": "/root/.openclaw", "mode": "rw"},
    "C:\\Users\\daemo\\workplace\\nest\\configs\\base": {"bind": "/app/configs/base", "mode": "ro"},
}
```

---

## Task List

### Task 1: Modify container creation - remove named volume, add direct mount

**Files:**
- Modify: `C:\Users\daemo\workplace\nest\nest-admin\backend\main.py:493-548`

- [ ] **Step 1: Read current container creation code**

Lines 493-548 - understand the current volume mount structure

- [ ] **Step 2: Remove named volume creation (lines 493-497)**

Delete:
```python
data_volume_name = f"nest_openclaw-{instance_id}-data"
try:
    CLIENT.volumes.get(data_volume_name)
except docker.errors.NotFound:
    CLIENT.volumes.create(data_volume_name)
```

- [ ] **Step 3: Update volumes dict (lines 513-517)**

Change from:
```python
volumes={
    data_volume_name: {"bind": "/root/.openclaw", "mode": "rw"},
    "C:\\Users\\daemo\\workplace\\nest\\configs\\base": {"bind": "/app/configs/base", "mode": "ro"},
    "C:\\Users\\daemo\\workplace\\nest\\configs\\instances\\" + name: {"bind": "/app/configs/instance", "mode": "ro"},
}
```

To:
```python
volumes={
    "C:\\Users\\daemo\\workplace\\nest\\configs\\instances\\" + name: {"bind": "/root/.openclaw", "mode": "rw"},
    "C:\\Users\\daemo\\workplace\\nest\\configs\\base": {"bind": "/app/configs/base", "mode": "ro"},
}
```

- [ ] **Step 4: Remove copy operation after container creation (lines 539-543)**

Delete:
```python
copy_result = container.exec_run(
    "sh -c 'cp /app/configs/instance/openclaw.json /root/.openclaw/openclaw.json'"
)
if copy_result.exit_code != 0:
    raise HTTPException(500, f"Failed to copy instance config: {copy_result.output.decode()}")
```

- [ ] **Step 5: Commit**

```bash
git add nest-admin/backend/main.py
git commit -m "refactor: remove named volume and copy in container creation"
```

---

### Task 2: Modify start_instance - remove copy operation

**Files:**
- Modify: `C:\Users\daemo\workplace\nest\nest-admin\backend\main.py:552-578`

- [ ] **Step 1: Read start_instance code**

Lines 552-578 - understand the current copy operation

- [ ] **Step 2: Remove copy operation (lines 572-576)**

Delete:
```python
copy_result = container.exec_run(
    "sh -c 'cp /app/configs/instance/openclaw.json /root/.openclaw/openclaw.json'"
)
if copy_result.exit_code != 0:
    raise HTTPException(500, f"Failed to copy instance config: {copy_result.output.decode()}")
```

- [ ] **Step 3: Commit**

```bash
git add nest-admin/backend/main.py
git commit -m "refactor: remove copy operation in start_instance"
```

---

### Task 3: Modify restart_instance - remove copy operation

**Files:**
- Modify: `C:\Users\daemo\workplace\nest\nest-admin\backend\main.py:592-605`

- [ ] **Step 1: Read restart_instance code**

Lines 592-605

- [ ] **Step 2: Remove copy operation (lines 599-603)**

Delete:
```python
copy_result = container.exec_run(
    "sh -c 'cp /app/configs/instance/openclaw.json /root/.openclaw/openclaw.json'"
)
if copy_result.exit_code != 0:
    raise HTTPException(500, f"Failed to copy instance config: {copy_result.output.decode()}")
```

- [ ] **Step 3: Commit**

```bash
git add nest-admin/backend/main.py
git commit -m "refactor: remove copy operation in restart_instance"
```

---

### Task 4: Update delete_instance - remove named volume removal

**Files:**
- Modify: `C:\Users\daemo\workplace\nest\nest-admin\backend\main.py` (find delete_instance)

- [ ] **Step 1: Find and read delete_instance function**

Search for `delete_instance` or `remove_instance`

- [ ] **Step 2: Remove named volume deletion code**

If it deletes `nest_openclaw-{id}-data` volume, remove that code since we're no longer using named volumes

- [ ] **Step 3: Commit**

```bash
git add nest-admin/backend/main.py
git commit -m "refactor: remove named volume cleanup from delete_instance"
```

---

## Summary of Changes

| Location | Change |
|----------|--------|
| Container creation | Remove named volume creation, change mount from `/app/configs/instance` to `/root/.openclaw` (rw) |
| start_instance | Remove copy operation |
| restart_instance | Remove copy operation |
| delete_instance | Remove named volume deletion |

## Benefits

1. **No more token mismatch** - config is mounted directly, no copy needed
2. **Persistence** - changes inside container persist to host directory
3. **Simpler** - fewer moving parts, no copy operations
4. **Correctness** - follows the principle that instance configs should be independent

## Testing

After implementing:
1. Rebuild nest-admin container: `docker compose -f nest-admin/nest-admin-compose.yml build`
2. Delete existing instances
3. Create new CPU and GPU instances
4. Verify both Control UIs work without token mismatch
5. Restart each instance and verify they still work