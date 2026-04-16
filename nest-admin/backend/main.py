import json
import logging
import os
import secrets
import shutil
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

import docker
from docker.models.containers import Container
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Nest Admin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CLIENT = docker.DockerClient(base_url="unix:///var/run/docker.sock")
STACK_NAME = "nest"
STACK_COMPOSE_PATH = os.environ.get("STACK_COMPOSE_PATH", "/app/compose/docker-compose.yml")
CONFIG_BASE_DIR = Path(os.environ.get("CONFIG_BASE_DIR", "/app/configs/base"))
CONFIG_INSTANCES_DIR = Path(os.environ.get("CONFIG_INSTANCES_DIR", "/app/configs/instances"))
PRESETS_DIR = Path(os.environ.get("PRESETS_DIR", "/app/configs/presets"))
PRESETS_KEYS_FILE = PRESETS_DIR / "keys.json"


class InstanceConfig(BaseModel):
    agents: Optional[dict] = None
    skills: Optional[dict] = None
    plugins: Optional[dict] = None
    memory: Optional[dict] = None
    logging: Optional[dict] = None
    cluster: Optional[dict] = None


class InstanceCreateRequest(BaseModel):
    name: str
    image: Optional[str] = "openclaw:pure-gpu"
    identity: Optional[str] = "empty"
    skills: Optional[list[str]] = []
    plugins: Optional[list[str]] = []
    modelProvider: Optional[str] = "minimax"
    channels: Optional[dict] = {}


def get_nest_containers() -> list[dict]:
    try:
        compose_containers = CLIENT.containers.list(
            filters={"label": [f"com.docker.compose.project={STACK_NAME}"]}
        )
    except Exception:
        compose_containers = []
    
    try:
        openclaw_containers = CLIENT.containers.list(
            filters={"label": ["openclaw.name"]}
        )
    except Exception:
        openclaw_containers = []
    
    all_containers = {c.id: c for c in compose_containers}
    for c in openclaw_containers:
        if c.id not in all_containers:
            all_containers[c.id] = c
    
    result = []
    for c in all_containers.values():
        labels = c.labels
        result.append({
            "name": c.name,
            "status": c.status,
            "image": c.image.tags[0] if c.image.tags else c.image.short_id,
            "instance_id": labels.get("openclaw.name", c.name),
            "created": c.attrs.get("Created", "")[:19].replace("T", " "),
            "ports": c.ports,
        })
    return result


def get_container_by_name(name: str) -> Optional[Container]:
    try:
        return CLIENT.containers.get(name)
    except docker.errors.NotFound:
        return None


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/instances")
async def list_instances():
    containers = get_nest_containers()
    running_names = {c["name"] for c in containers}
    
    instances = []
    for c in containers:
        config_path = CONFIG_INSTANCES_DIR / c["instance_id"] / "openclaw.json"
        meta_path = CONFIG_INSTANCES_DIR / c["instance_id"] / "meta.json"
        config = {}
        meta = {}
        if config_path.exists():
            config = json.loads(config_path.read_text())
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
        instances.append({
            **c,
            "config": config,
            "config_exists": config_path.exists(),
            "image": meta.get("image", "openclaw:pure-gpu"),
        })
    
    configured_dirs = []
    if CONFIG_INSTANCES_DIR.exists():
        for d in CONFIG_INSTANCES_DIR.iterdir():
            if d.is_dir() and d.name not in running_names:
                configured_dirs.append(d.name)
    
    for name in configured_dirs:
        config_path = CONFIG_INSTANCES_DIR / name / "openclaw.json"
        meta_path = CONFIG_INSTANCES_DIR / name / "meta.json"
        config = {}
        meta = {}
        if config_path.exists():
            config = json.loads(config_path.read_text())
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
        instances.append({
            "name": name,
            "status": "stopped",
            "instance_id": name,
            "image": meta.get("image", "openclaw:pure-gpu"),
            "created": "",
            "ports": {},
            "config": config,
            "config_exists": True,
        })
    
    return instances


@app.get("/api/instances/{name}")
async def get_instance(name: str):
    container = get_container_by_name(name)
    if not container:
        raise HTTPException(404, f"Instance {name} not found")
    
    config_path = CONFIG_INSTANCES_DIR / name / "openclaw.json"
    meta_path = CONFIG_INSTANCES_DIR / name / "meta.json"
    config = {}
    meta = {}
    if config_path.exists():
        config = json.loads(config_path.read_text())
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
    
    container.reload()
    return {
        "name": container.name,
        "status": container.status,
        "image": meta.get("image", "openclaw:pure-gpu"),
        "instance_id": name,
        "config": config,
        "created": container.attrs.get("Created", "")[:19].replace("T", " "),
        "ports": container.ports,
    }


def load_preset_keys() -> dict:
    if PRESETS_KEYS_FILE.exists():
        try:
            return json.loads(PRESETS_KEYS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {"version": 1, "keys": {}, "defaultProvider": "minimax"}
    return {"version": 1, "keys": {}, "defaultProvider": "minimax"}

def save_preset_keys(data: dict):
    if not isinstance(data, dict) or "keys" not in data:
        raise ValueError("Invalid data structure: expected dict with 'keys' field")
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        PRESETS_KEYS_FILE.write_text(json.dumps(data, indent=2))
    except (OSError, IOError) as e:
        raise IOError(f"Failed to write preset keys: {e}")

def mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return "****"
    return key[:4] + "****" + key[-4]

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
        logger.warning(f"Identity preset not found: {identity_id}")
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
        if not src_dir.exists():
            logger.warning(f"Skill preset not found: {skill_id}")
            continue
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
        if not src_dir.exists():
            logger.warning(f"Plugin preset not found: {plugin_id}")
            continue
        dst_dir = plugins_dir / plugin_id
        dst_dir.mkdir(parents=True, exist_ok=True)
        for f in src_dir.iterdir():
            if f.is_file():
                (dst_dir / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")

def get_next_instance_id() -> int:
    max_id = 0
    for d in CONFIG_INSTANCES_DIR.iterdir():
        if d.is_dir():
            config_file = d / "openclaw.json"
            if config_file.exists():
                try:
                    config = json.loads(config_file.read_text())
                    instance_id = config.get("cluster", {}).get("instanceId", 0)
                    if instance_id > max_id:
                        max_id = instance_id
                except Exception:
                    pass
    return max_id + 1


def find_available_ports(start_port: int = 18790, count: int = 3) -> list:
    used_ports = set()
    for c in CLIENT.containers.list(all=True):
        for port, bindings in (c.ports or {}).items():
            if bindings:
                for b in bindings:
                    if b.get("HostPort"):
                        used_ports.add(int(b["HostPort"]))
    
    available = []
    port = start_port
    while len(available) < count:
        if port not in used_ports:
            available.append(port)
        port += 1
    return available


@app.post("/api/instances")
async def create_instance(data: InstanceCreateRequest):
    name = data.name
    if not isinstance(name, str) or not name.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(400, "name must be alphanumeric with dashes/underscores only")
    instance_dir = CONFIG_INSTANCES_DIR / name
    if instance_dir.exists():
        raise HTTPException(400, f"Instance {name} already exists")

    instance_id = get_next_instance_id()
    instance_dir.mkdir(parents=True, exist_ok=True)

    token = secrets.token_hex(16)

    keys_data = load_preset_keys()

    config = build_instance_config(instance_id, name, token, data, keys_data)
    (instance_dir / "openclaw.json").write_text(json.dumps(config, indent=2))

    meta = {"image": data.image or "openclaw:pure-gpu"}
    (instance_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    create_instance_directories(instance_dir)

    if data.identity and data.identity != "empty":
        apply_identity_to_instance(instance_dir, data.identity)

    if data.skills:
        apply_skills_to_instance(instance_dir, data.skills)

    if data.plugins:
        apply_plugins_to_instance(instance_dir, data.plugins, keys_data)

    return {"name": name, "instance_id": instance_id, "status": "created"}

def build_instance_config(instance_id: int, name: str, token: str, data: InstanceCreateRequest, keys_data: dict) -> dict:
    """构建实例的 openclaw.json"""
    config = {
        "gateway": {
            "mode": "local",
            "bind": "lan",
            "controlUi": {
                "dangerouslyDisableDeviceAuth": True,
                "allowInsecureAuth": True,
                "allowedOrigins": ["*"]
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

    model_provider = data.modelProvider or keys_data.get("defaultProvider", "minimax")
    if model_provider in keys_data.get("keys", {}):
        provider_keys = keys_data["keys"][model_provider]
        if "apiKey" in provider_keys:
            env_var_name = f"{model_provider.upper()}_API_KEY"
            config["env"] = {env_var_name: provider_keys["apiKey"]}

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

    if data.plugins:
        config["plugins"] = {
            "allow": data.plugins,
            "load": {"paths": ["/app/extensions", "/root/.openclaw/extensions"]}
        }

    config["cluster"] = {
        "instanceId": instance_id,
        "instanceName": name
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


@app.delete("/api/instances/{name}")
async def delete_instance(name: str):
    container = get_container_by_name(name)
    if container:
        try:
            container.stop(timeout=5)
        except Exception:
            pass
        try:
            container.remove()
        except Exception:
            pass
    
    instance_dir = CONFIG_INSTANCES_DIR / name
    if instance_dir.exists():
        shutil.rmtree(instance_dir)
    
    return {"name": name, "status": "deleted"}


@app.patch("/api/instances/{name}")
async def update_instance(name: str, data: InstanceConfig):
    instance_dir = CONFIG_INSTANCES_DIR / name
    config_path = instance_dir / "openclaw.json"
    
    config = {}
    if config_path.exists():
        config = json.loads(config_path.read_text())
    
    update_data = data.model_dump(exclude_none=True)
    config.update(update_data)
    
    instance_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2))
    
    return {"name": name, "status": "updated"}


@app.post("/api/instances/{name}/start")
async def start_instance(name: str):
    container = get_container_by_name(name)
    if not container:
        config_path = CONFIG_INSTANCES_DIR / name / "openclaw.json"
        if not config_path.exists():
            raise HTTPException(404, f"Instance {name} not found and no configuration")
        
        try:
            config = json.loads(config_path.read_text())
            instance_id = config.get("cluster", {}).get("instanceId", 1)
            
            used_ports = set()
            for c in CLIENT.containers.list(all=True):
                for port, bindings in (c.ports or {}).items():
                    if bindings:
                        for b in bindings:
                            if b.get("HostPort"):
                                used_ports.add(int(b["HostPort"]))
            
            base_port = 18790 + (instance_id - 1) * 10
            available_ports = []
            for offset in range(50):
                test_port = base_port + offset * 10
                if test_port not in used_ports and test_port + 1 not in used_ports and test_port + 2 not in used_ports:
                    available_ports = [test_port, test_port + 1, test_port + 2]
                    break
            
            if len(available_ports) != 3:
                for p in range(18800, 19000):
                    if p not in used_ports and p + 1 not in used_ports and p + 2 not in used_ports:
                        available_ports = [p, p + 1, p + 2]
                        break
            
            if len(available_ports) != 3:
                raise HTTPException(500, "No available ports found")
            
            network = CLIENT.networks.get("nest_openclaw-net")
            network.reload()
            existing_ips = set()
            for container_info in network.attrs.get("Containers", {}).values():
                if container_info.get("IPv4Address"):
                    ip = container_info["IPv4Address"].split("/")[0]
                    existing_ips.add(ip)
            
            base_ip_num = 20
            for i in range(100, 254):
                ip = f"172.28.0.{i}"
                if ip not in existing_ips:
                    break

            meta_path = CONFIG_INSTANCES_DIR / name / "meta.json"
            meta = {}
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
            image_name = meta.get("image", "openclaw:pure-gpu")
            container = CLIENT.containers.run(
                image=image_name,
                name=name,
                detach=True,
                ports={
                    "18789/tcp": available_ports[0],
                    "18790/tcp": available_ports[1],
                    "5555/tcp": available_ports[2],
                },
                volumes={
                    "C:\\Users\\daemo\\workplace\\nest\\configs\\instances\\" + name: {"bind": "/root/.openclaw", "mode": "rw"},
                    "C:\\Users\\daemo\\workplace\\nest\\configs\\base": {"bind": "/app/configs/base", "mode": "ro"},
                },
                environment={
                    "INSTANCE_NAME": name,
                    "INSTANCE_ID": str(instance_id),
                    "NODE_ENV": "production",
                    "TZ": "Asia/Shanghai",
                    "MINIMAX_API_KEY": os.environ.get("MINIMAX_API_KEY", ""),
                    "AUTOGLM_API_KEY": os.environ.get("AUTOGLM_API_KEY", os.environ.get("MINIMAX_API_KEY", "")),
                    "FEISHU_APP_ID": os.environ.get("FEISHU_APP_ID", "dummy"),
                    "FEISHU_APP_SECRET": os.environ.get("FEISHU_APP_SECRET", "dummy"),
                    "FEISHU_VERIFICATION_TOKEN": os.environ.get("FEISHU_VERIFICATION_TOKEN", "dummy"),
                },
                privileged=True,
                restart_policy={"Name": "unless-stopped"},
                labels={
                    "com.docker.compose.project": STACK_NAME,
                    "com.docker.compose.service": name,
                    "openclaw.name": name,
                    "openclaw.cluster": "enabled",
                },
            )

            network = CLIENT.networks.get("nest_openclaw-net")
            network.connect(container, ipv4_address=ip)
            
            return {"name": name, "status": "created and started", "ports": available_ports}
        except Exception as e:
            raise HTTPException(500, f"Failed to create container: {str(e)}")
    
    if container.status == "running":
        return {"name": name, "status": "already running"}

    meta_path = CONFIG_INSTANCES_DIR / name / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        desired_image = meta.get("image", "openclaw:pure-gpu")
        current_image = container.image.tags[0] if container.image.tags else container.image.short_id
        if desired_image != current_image:
            logger.warning(
                f"Container '{name}' was created with image '{current_image}' "
                f"but meta.json specifies '{desired_image}'. "
                f"The container may need to be recreated to use the new image."
            )

    container.start()

    import time
    time.sleep(2)

    return {"name": name, "status": "started"}


@app.post("/api/instances/{name}/stop")
async def stop_instance(name: str):
    container = get_container_by_name(name)
    if not container:
        raise HTTPException(404, f"Instance {name} not found")
    if container.status != "running":
        return {"name": name, "status": "already stopped"}
    container.stop(timeout=10)
    return {"name": name, "status": "stopped"}


@app.post("/api/instances/{name}/restart")
async def restart_instance(name: str):
    container = get_container_by_name(name)
    if not container:
        raise HTTPException(404, f"Instance {name} not found")
    container.restart(timeout=30)

    return {"name": name, "status": "restarted"}


@app.post("/api/stack/start")
async def start_stack():
    compose_dir = Path(STACK_COMPOSE_PATH).parent
    try:
        result = subprocess.run(
            ["docker-compose", "up", "-d"],
            cwd=compose_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            return {"status": "error", "message": result.stderr}
        return {"status": "started", "output": result.stdout}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Timeout during stack start"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/stack/stop")
async def stop_stack():
    compose_dir = Path(STACK_COMPOSE_PATH).parent
    try:
        result = subprocess.run(
            ["docker-compose", "down"],
            cwd=compose_dir,
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode != 0:
            return {"status": "error", "message": result.stderr}
        return {"status": "stopped", "output": result.stdout}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Timeout during stack stop"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/stack/status")
async def stack_status():
    containers = get_nest_containers()
    running = sum(1 for c in containers if c["status"] == "running")
    return {
        "total": len(containers),
        "running": running,
        "containers": containers
    }


@app.get("/api/config/{name}")
async def get_config(name: str):
    config_path = CONFIG_INSTANCES_DIR / name / "openclaw.json"
    if not config_path.exists():
        raise HTTPException(404, f"Config for {name} not found")
    return json.loads(config_path.read_text())


@app.put("/api/config/{name}")
async def save_config(name: str, data: dict):
    instance_dir = CONFIG_INSTANCES_DIR / name
    config_path = instance_dir / "openclaw.json"
    instance_dir.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2))
    return {"name": name, "status": "saved"}


@app.get("/api/instances/{name}/logs")
async def get_logs(name: str, tail: int = 100):
    container = get_container_by_name(name)
    if not container:
        raise HTTPException(404, f"Instance {name} not found")
    logs = container.logs(tail=tail, stdout=True, stderr=True, timestamps=True)
    return {"logs": logs.decode("utf-8", errors="replace")}


@app.post("/api/instances/{name}/pairing/approve")
async def approve_pairing(name: str):
    container = get_container_by_name(name)
    if not container:
        raise HTTPException(404, f"Instance {name} not found")
    
    try:
        result = container.exec_run("openclaw devices list --json")
        if result.exit_code != 0:
            return {"status": "error", "message": result.output.decode()}
        
        import json
        try:
            devices_data = json.loads(result.output.decode())
        except json.JSONDecodeError:
            return {"status": "error", "message": "Failed to parse devices list"}
        
        pending_devices = devices_data.get("pending", [])
        
        if not pending_devices:
            return {"status": "no_pending", "message": "No pending devices to approve"}
        
        approved = []
        for device in pending_devices:
            token = device.get("token")
            if token:
                approve_result = container.exec_run(f"openclaw devices approve {token}")
                if approve_result.exit_code == 0:
                    approved.append(token)
        
        return {
            "status": "approved",
            "approved_count": len(approved),
            "approved_tokens": approved
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/base-config")
async def get_base_config():
    config_path = CONFIG_BASE_DIR / "openclaw.json"
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {}


@app.put("/api/base-config")
async def save_base_config(data: dict):
    config_path = CONFIG_BASE_DIR / "openclaw.json"
    CONFIG_BASE_DIR.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2))
    return {"status": "saved"}


PRESETS = {
    "skills": [
        {"id": "github", "name": "GitHub", "description": "GitHub API integration for repository management"},
        {"id": "web-search", "name": "Web Search", "description": "Search the web for information"},
        {"id": "code-gen", "name": "Code Generation", "description": "Generate and edit code files"},
        {"id": "summarize", "name": "Summarize", "description": "Summarize text and documents"},
        {"id": "file-operations", "name": "File Operations", "description": "Read, write, and manage files"},
        {"id": "bash", "name": "Bash Terminal", "description": "Execute bash commands"},
        {"id": "browser", "name": "Browser", "description": "Web browser automation"},
        {"id": "recipe", "name": "Recipe", "description": "Execute predefined workflows"},
    ],
    "channels": [
        {
            "id": "telegram",
            "name": "Telegram",
            "description": "Telegram 机器人",
            "fields": [
                {"id": "botToken", "name": "Bot Token", "type": "password", "placeholder": "123456:ABC-DEF..."},
                {"id": "dmPolicy", "name": "DM策略", "type": "select", "options": ["open", "allowlist", "denylist"]},
                {"id": "allowFrom", "name": "允许来源", "type": "text", "placeholder": "* 或用户ID列表"},
                {"id": "groupPolicy", "name": "群组策略", "type": "select", "options": ["allowlist", "denylist"]},
                {"id": "streaming", "name": "流式响应", "type": "select", "options": ["partial", "full", "off"]},
            ]
        },
        {
            "id": "feishu",
            "name": "飞书",
            "description": "飞书机器人 (支持 QR 码配置)",
            "fields": [
                {"id": "appId", "name": "App ID", "type": "text", "placeholder": "cli_a..."},
                {"id": "appSecret", "name": "App Secret", "type": "password", "placeholder": "..."},
                {"id": "verificationToken", "name": "Verification Token", "type": "password", "placeholder": "..."},
                {"id": "botName", "name": "机器人名称", "type": "text", "placeholder": "OpenClaw"},
                {"id": "dmPolicy", "name": "DM策略", "type": "select", "options": ["pairing", "open", "allowlist", "disabled"]},
                {"id": "allowFrom", "name": "允许来源", "type": "text", "placeholder": "* 或用户ID列表"},
            ]
        },
        {
            "id": "weixin",
            "name": "企业微信",
            "description": "企业微信机器人",
            "fields": [
                {"id": "corpId", "name": "企业ID", "type": "text", "placeholder": "..."},
                {"id": "agentId", "name": "应用AgentID", "type": "text", "placeholder": "..."},
                {"id": "corpSecret", "name": "应用Secret", "type": "password", "placeholder": "..."},
            ]
        },
    ],
    "plugins": [
        {"id": "feishu", "name": "飞书", "description": "飞书机器人集成", "enabled": False},
        {"id": "dingtalk", "name": "钉钉", "description": "钉钉机器人集成", "enabled": False},
        {"id": "wechat", "name": "企业微信", "description": "企业微信机器人集成", "enabled": False},
        {"id": "slack", "name": "Slack", "description": "Slack webhook integration", "enabled": False},
        {"id": "docker", "name": "Docker", "description": "Docker container management", "enabled": False},
        {"id": "database", "name": "Database", "description": "Database operations", "enabled": False},
        {"id": "active-memory", "name": "Active Memory", "description": "主动记忆插件 - 在回复前自动检索相关记忆", "enabled": False},
    ],
    "model_providers": [
        {
            "id": "minimax",
            "name": "MiniMax",
            "baseUrl": "https://api.minimaxi.com/anthropic",
            "apiType": "anthropic-messages",
            "authHeader": True,
            "models": [
                {"id": "MiniMax-M2.7-highspeed", "name": "M2.7 超速版", "input": ["text"], "contextWindow": 200000, "maxTokens": 8192, "reasoning": False, "cost": {"input": 15, "output": 60, "cacheRead": 2, "cacheWrite": 10}},
                {"id": "MiniMax-M2.5-highspeed", "name": "M2.5 超速版", "input": ["text"], "contextWindow": 200000, "maxTokens": 8192, "reasoning": True, "cost": {"input": 0.3, "output": 1.2, "cacheRead": 0.03, "cacheWrite": 0.12}},
                {"id": "MiniMax-M2.5", "name": "M2.5 标准版", "input": ["text"], "contextWindow": 200000, "maxTokens": 8192, "reasoning": True, "cost": {"input": 0.3, "output": 1.2, "cacheRead": 0.03, "cacheWrite": 0.12}},
                {"id": "MiniMax-VL-01", "name": "VL 视觉版", "input": ["text", "image"], "contextWindow": 200000, "maxTokens": 8192, "reasoning": False, "cost": {"input": 0.3, "output": 1.2, "cacheRead": 0.03, "cacheWrite": 0.12}},
            ]
        },
        {
            "id": "zhipu",
            "name": "智谱GLM",
            "baseUrl": "https://open.bigmodel.cn/api/paas/v4",
            "apiType": "anthropic-messages",
            "authHeader": True,
            "models": [
                {"id": "glm-4-plus", "name": "GLM-4 Plus", "input": ["text"], "contextWindow": 128000, "maxTokens": 8192, "reasoning": True},
                {"id": "glm-4-flash", "name": "GLM-4 Flash", "input": ["text"], "contextWindow": 128000, "maxTokens": 8192, "reasoning": True},
                {"id": "glm-4v-flash", "name": "GLM-4V 视觉版", "input": ["text", "image"], "contextWindow": 128000, "maxTokens": 8192, "reasoning": False},
            ]
        },
        {
            "id": "kimi",
            "name": "月之暗面 Kimi",
            "baseUrl": "https://api.moonshot.cn/v1",
            "apiType": "chat/completions",
            "authHeader": True,
            "models": [
                {"id": "moonshot-v1-8k", "name": "Kimi 8K", "input": ["text"], "contextWindow": 8000, "maxTokens": 4096, "reasoning": False},
                {"id": "moonshot-v1-32k", "name": "Kimi 32K", "input": ["text"], "contextWindow": 32000, "maxTokens": 4096, "reasoning": False},
                {"id": "moonshot-v1-128k", "name": "Kimi 128K", "input": ["text"], "contextWindow": 128000, "maxTokens": 4096, "reasoning": False},
            ]
        },
        {
            "id": "doubao",
            "name": "豆包 Doubao",
            "baseUrl": "https://ark.cn-beijing.volces.com/api/v3",
            "apiType": "chat/completions",
            "authHeader": True,
            "models": [
                {"id": "doubao-pro-32k", "name": "豆包 Pro 32K", "input": ["text"], "contextWindow": 32000, "maxTokens": 4096, "reasoning": False},
                {"id": "doubao-pro-128k", "name": "豆包 Pro 128K", "input": ["text"], "contextWindow": 128000, "maxTokens": 4096, "reasoning": False},
                {"id": "doubao-lite-32k", "name": "豆包 Lite 32K", "input": ["text"], "contextWindow": 32000, "maxTokens": 4096, "reasoning": False},
            ]
        },
        {
            "id": "qwen",
            "name": "阿里 Qwen",
            "baseUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "apiType": "chat/completions",
            "authHeader": True,
            "models": [
                {"id": "qwen-turbo", "name": "Qwen Turbo", "input": ["text"], "contextWindow": 8192, "maxTokens": 4096, "reasoning": False},
                {"id": "qwen-plus", "name": "Qwen Plus", "input": ["text"], "contextWindow": 131072, "maxTokens": 4096, "reasoning": True},
                {"id": "qwen-max", "name": "Qwen Max", "input": ["text"], "contextWindow": 32768, "maxTokens": 4096, "reasoning": True},
                {"id": "qwen-vl-plus", "name": "Qwen VL Plus", "input": ["text", "image"], "contextWindow": 32768, "maxTokens": 4096, "reasoning": False},
            ]
        },
        {
            "id": "ernie",
            "name": "百度文心 ERNIE",
            "baseUrl": "https://qianfan.ai.baidubce.com/v2",
            "apiType": "chat/completions",
            "authHeader": True,
            "models": [
                {"id": "ernie-4.0-8k", "name": "ERNIE 4.0 8K", "input": ["text"], "contextWindow": 8000, "maxTokens": 4096, "reasoning": True},
                {"id": "ernie-4.0-32k", "name": "ERNIE 4.0 32K", "input": ["text"], "contextWindow": 32000, "maxTokens": 4096, "reasoning": True},
                {"id": "ernie-3.5-8k", "name": "ERNIE 3.5 8K", "input": ["text"], "contextWindow": 8000, "maxTokens": 4096, "reasoning": False},
            ]
        },
        {
            "id": "lmstudio",
            "name": "LM Studio",
            "baseUrl": "http://localhost:1234/v1",
            "apiType": "chat/completions",
            "authHeader": False,
            "models": [
                {"id": "local-model", "name": "Local Model", "input": ["text"], "contextWindow": 128000, "maxTokens": 4096, "reasoning": False, "cost": {"input": 0, "output": 0}},
            ]
        },
        {
            "id": "codex",
            "name": "Codex",
            "baseUrl": "https://api.codex.com/v2",
            "apiType": "chat/completions",
            "authHeader": True,
            "models": [
                {"id": "gpt-5.4", "name": "GPT-5.4", "input": ["text"], "contextWindow": 200000, "maxTokens": 8192, "reasoning": True, "cost": {"input": 0, "output": 0}},
                {"id": "gpt-4.1", "name": "GPT-4.1", "input": ["text"], "contextWindow": 128000, "maxTokens": 8192, "reasoning": True, "cost": {"input": 0, "output": 0}},
            ]
        },
    ],
    "workspace_files": [
        {"id": "AGENTS.md", "name": "AGENTS.md", "description": "任务管理与分配规则"},
        {"id": "IDENTITY.md", "name": "IDENTITY.md", "description": "Agent身份定义"},
        {"id": "SOUL.md", "name": "SOUL.md", "description": "Agent个性与原则"},
        {"id": "TOOLS.md", "name": "TOOLS.md", "description": "本地工具配置笔记"},
        {"id": "USER.md", "name": "USER.md", "description": "用户信息"},
        {"id": "MEMORY.md", "name": "MEMORY.md", "description": "长期记忆"},
        {"id": "BOOTSTRAP.md", "name": "BOOTSTRAP.md", "description": "首次运行引导"},
        {"id": "HEARTBEAT.md", "name": "HEARTBEAT.md", "description": "心跳任务指令"},
    ],
    "core_templates": [
        {
            "id": "default",
            "name": "默认配置",
            "description": "标准的 OpenClaw 实例配置",
            "content": """# OpenClaw 实例配置

## 基本信息
- 实例名称: {instance_name}
- 实例ID: {instance_id}

## 技能
已启用基础技能组合

## 记忆
使用默认记忆存储

## 日志
- 级别: info
"""
        },
        {
            "id": "development",
            "name": "开发环境",
            "description": "适合软件开发的配置",
            "content": """# OpenClaw 开发环境配置

## 基本信息
- 实例名称: {instance_name}
- 实例ID: {instance_id}

## 技能
- github: 代码仓库管理
- bash: 命令行操作
- file-operations: 文件操作
- code-gen: 代码生成

## 记忆
- 启用代码理解记忆
- 路径: /root/.openclaw/memory-{instance_id}.db

## 日志
- 级别: debug
- 详细模式已启用

## 开发工具
- 启用语法高亮
- 启用代码补全
"""
        },
        {
            "id": "research",
            "name": "研究助手",
            "description": "适合研究工作的配置",
            "content": """# OpenClaw 研究助手配置

## 基本信息
- 实例名称: {instance_name}
- 实例ID: {instance_id}

## 技能
- web-search: 网络搜索
- summarize: 内容摘要
- file-operations: 文件操作

## 记忆
- 启用研究资料记忆
- 路径: /root/.openclaw/memory-research-{instance_id}.db

## 日志
- 级别: info

## 研究工具
- 启用网络搜索
- 启用文档摘要
"""
        },
        {
            "id": "operations",
            "name": "运维管理",
            "description": "适合运维管理的配置",
            "content": """# OpenClaw 运维管理配置

## 基本信息
- 实例名称: {instance_name}
- 实例ID: {instance_id}

## 技能
- bash: 命令行操作
- docker: 容器管理
- file-operations: 文件操作
- web-search: 问题排查

## 记忆
- 启用运维知识库
- 路径: /root/.openclaw/memory-ops-{instance_id}.db

## 日志
- 级别: debug
- 文件: /root/.openclaw/logs/{instance_name}.log

## 监控
- 启用健康检查
- 启用错误告警
"""
        },
        {
            "id": "empty",
            "name": "空白模板",
            "description": "空白模板，从头开始配置",
            "content": """# OpenClaw 配置 - {instance_name}

<!-- 在此编辑您的实例配置 -->

## 集群
- instanceId: {instance_id}
- instanceName: {instance_name}

"""
        },
    ]
}


@app.get("/api/presets/core-templates")
async def get_core_templates():
    return PRESETS["core_templates"]


@app.get("/api/presets/model-providers")
async def get_model_providers():
    return PRESETS["model_providers"]


@app.get("/api/presets/workspace-files")
async def get_workspace_files():
    return PRESETS["workspace_files"]


@app.get("/api/presets/channels")
async def get_channel_presets():
    return PRESETS["channels"]


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

@app.put("/api/presets/keys")
async def update_preset_keys(data: dict):
    """更新预制 Keys"""
    if not isinstance(data, dict):
        raise HTTPException(400, "Invalid data format")
    required_fields = ("version", "keys", "defaultProvider")
    if not all(field in data for field in required_fields):
        raise HTTPException(400, f"Missing required fields: {required_fields}")
    save_preset_keys(data)
    return {"status": "saved"}


def sanitize_preset_id(preset_id: str) -> str:
    """Sanitize preset ID to prevent path traversal"""
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', preset_id):
        raise HTTPException(400, "Invalid preset ID")
    return preset_id


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
    identity_id = sanitize_preset_id(identity_id)
    identity_dir = PRESETS_DIR / "identities" / identity_id
    if not identity_dir.exists():
        raise HTTPException(404, f"Identity {identity_id} not found")
    files = {}
    for fname in ["SOUL.md", "USER.md", "IDENTITY.md", "HEARTBEAT.md"]:
        fpath = identity_dir / fname
        if fpath.exists():
            files[fname] = fpath.read_text(encoding="utf-8")
    return {"id": identity_id, "files": files}

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
    skill_id = sanitize_preset_id(skill_id)
    skill_dir = PRESETS_DIR / "skills" / skill_id
    if not skill_dir.exists():
        raise HTTPException(404, f"Skill {skill_id} not found")
    skill_md = skill_dir / "SKILL.md"
    content = ""
    if skill_md.exists():
        content = skill_md.read_text(encoding="utf-8")
    return {"id": skill_id, "content": content}

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


@app.get("/api/instances/{name}/workspace/{filename}")
async def get_instance_workspace_file(name: str, filename: str):
    workspace_dir = CONFIG_INSTANCES_DIR / name / "workspace"
    file_path = workspace_dir / filename
    if file_path.exists():
        return {"content": file_path.read_text(encoding="utf-8")}
    return {"content": ""}


@app.put("/api/instances/{name}/workspace/{filename}")
async def save_instance_workspace_file(name: str, filename: str, data: dict):
    workspace_dir = CONFIG_INSTANCES_DIR / name / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    file_path = workspace_dir / filename
    content = data.get("content", "")
    file_path.write_text(content, encoding="utf-8")
    return {"name": name, "filename": filename, "status": "saved"}


@app.get("/api/instances/{name}/workspace")
async def list_instance_workspace_files(name: str):
    workspace_dir = CONFIG_INSTANCES_DIR / name / "workspace"
    files = {}
    if workspace_dir.exists():
        for f in workspace_dir.iterdir():
            if f.is_file() and f.suffix == ".md":
                files[f.name] = f.read_text(encoding="utf-8")[:500]
    return {"files": files}


@app.get("/api/instances/{name}/core-md")
async def get_instance_core_md(name: str):
    core_md_path = CONFIG_INSTANCES_DIR / name / "core.md"
    if core_md_path.exists():
        return {"content": core_md_path.read_text(encoding="utf-8")}
    return {"content": ""}


@app.put("/api/instances/{name}/core-md")
async def save_instance_core_md(name: str, data: dict):
    core_md_path = CONFIG_INSTANCES_DIR / name / "core.md"
    instance_dir = CONFIG_INSTANCES_DIR / name
    instance_dir.mkdir(parents=True, exist_ok=True)
    content = data.get("content", "")
    core_md_path.write_text(content, encoding="utf-8")
    return {"name": name, "status": "saved"}


@app.post("/api/instances/{name}/apply-template")
async def apply_core_template(name: str, data: dict):
    template_id = data.get("template_id")
    template = next((t for t in PRESETS["core_templates"] if t["id"] == template_id), None)
    if not template:
        raise HTTPException(404, f"Template {template_id} not found")
    
    content = template["content"].format(
        instance_name=name,
        instance_id=data.get("instance_id", 1)
    )
    core_md_path = CONFIG_INSTANCES_DIR / name / "core.md"
    instance_dir = CONFIG_INSTANCES_DIR / name
    instance_dir.mkdir(parents=True, exist_ok=True)
    core_md_path.write_text(content, encoding="utf-8")
    return {"name": name, "status": "applied", "template_id": template_id}


@app.get("/api/instances/{name}/full-config")
async def get_instance_full_config(name: str):
    config_path = CONFIG_INSTANCES_DIR / name / "openclaw.json"
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {}


@app.put("/api/instances/{name}/full-config")
async def save_instance_full_config(name: str, data: dict):
    instance_dir = CONFIG_INSTANCES_DIR / name
    instance_dir.mkdir(parents=True, exist_ok=True)
    config_path = instance_dir / "openclaw.json"
    config_path.write_text(json.dumps(data, indent=2))
    return {"name": name, "status": "saved"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
