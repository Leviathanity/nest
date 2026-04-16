import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import docker
from docker.models.containers import Container
from docker.types import Mount
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import yaml

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
COMPOSE_DIR = Path(os.environ.get("COMPOSE_DIR", "/app/compose"))
CONFIG_BASE_DIR = Path(os.environ.get("CONFIG_BASE_DIR", "/app/configs/base"))
CONFIG_INSTANCES_DIR = Path(os.environ.get("CONFIG_INSTANCES_DIR", "/app/configs/instances"))
COMPOSE_FILE = COMPOSE_DIR / "docker-compose.yml"
BACKUP_COMPOSE_FILE = COMPOSE_DIR / "docker-compose.yml.backup"


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
    model: Optional[str] = "minimax/MiniMax-M2.7-highspeed"
    apiKey: Optional[str] = None
    channels: Optional[dict] = {}


class WebhookConfig(BaseModel):
    url: str = ""
    enabled: bool = False


def get_nest_containers() -> list[dict]:
    containers = CLIENT.containers.list(
        filters={"label": [f"com.docker.compose.project={STACK_NAME}"]}
    )
    result = []
    for c in containers:
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


def run_docker_compose(command: list[str], cwd: Optional[str] = None) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            command,
            cwd=cwd or str(COMPOSE_DIR),
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", "docker-compose not found"
    except Exception as e:
        return -1, "", str(e)


def get_next_ip() -> str:
    used_ips = set()
    try:
        for container in CLIENT.containers.list(all=True):
            if container.attrs.get("NetworkSettings", {}).get("Networks"):
                for net_name, net_info in container.attrs["NetworkSettings"]["Networks"].items():
                    if net_name.startswith("nest"):
                        ip = net_info.get("IPAddress")
                        if ip and ip.startswith("172.28."):
                            used_ips.add(ip)
    except Exception:
        pass

    base_ip = "172.28.0."
    for i in range(10, 255):
        candidate = f"{base_ip}{i}"
        if candidate not in used_ips:
            return candidate
    return f"{base_ip}10"


def get_next_ports() -> tuple[int, int, int]:
    used_ports = set()
    try:
        for container in CLIENT.containers.list(all=True):
            for port, bindings in container.ports.items():
                if bindings:
                    for binding in bindings:
                        if binding.get("HostPort"):
                            used_ports.add(int(binding["HostPort"]))
    except Exception:
        pass

    def find_next_port(start: int) -> int:
        for p in range(start, 65535):
            if p not in used_ports:
                used_ports.add(p)
                return p
        return start
    
    return (find_next_port(18792), find_next_port(18794), find_next_port(5556))


def backup_compose_file():
    if COMPOSE_FILE.exists():
        shutil.copy2(COMPOSE_FILE, BACKUP_COMPOSE_FILE)


def get_next_instance_id() -> int:
    max_id = 0
    if COMPOSE_FILE.exists():
        with open(COMPOSE_FILE, "r") as f:
            compose_content = yaml.safe_load(f) or {}
        volumes = compose_content.get("volumes", {})
        for vol_name in volumes.keys():
            if vol_name.startswith("openclaw-") and vol_name.endswith("-data"):
                try:
                    vol_id = int(vol_name.replace("openclaw-", "").replace("-data", ""))
                    if vol_id > max_id:
                        max_id = vol_id
                except ValueError:
                    pass
    return max_id + 1


def add_service_to_compose(name: str, image: str, ip: str, http_port: int, app_port: int, data_port: int, api_key: Optional[str] = None) -> bool:
    backup_compose_file()
    try:
        compose_content = {}
        if COMPOSE_FILE.exists():
            with open(COMPOSE_FILE, "r") as f:
                compose_content = yaml.safe_load(f) or {}

        services = compose_content.get("services", {})
        instance_id = get_next_instance_id()
        volume_name = f"openclaw-{instance_id}-data"

        services[name] = {
            "image": image,
            "container_name": name,
            "networks": {
                "openclaw-net": {"ipv4_address": ip}
            },
            "volumes": [
                f"{volume_name}:/root/.openclaw",
                f"./configs/base:/app/configs/base:ro",
                f"./configs/instances/{name}:/app/configs/instance:ro"
            ],
            "ports": [
                f"{http_port}:18789",
                f"{app_port}:18790",
                f"{data_port}:5555"
            ],
            "environment": [
                f"INSTANCE_NAME={name}",
                f"INSTANCE_ID={instance_id}",
                "NODE_ENV=production",
                "TZ=Asia/Shanghai",
                f"MINIMAX_API_KEY={api_key if api_key else '${MINIMAX_API_KEY}'}",
                f"AUTOGLM_API_KEY={api_key if api_key else '${MINIMAX_API_KEY}'}",
                "FEISHU_APP_ID=dummy",
                "FEISHU_APP_SECRET=dummy",
                "FEISHU_VERIFICATION_TOKEN=dummy"
            ],
            "privileged": True,
            "restart": "unless-stopped",
            "labels": [
                f"openclaw.name={name}",
                "openclaw.cluster=enabled"
            ]
        }

        networks = compose_content.get("networks", {})
        if "openclaw-net" not in networks:
            networks["openclaw-net"] = {
                "driver": "bridge",
                "ipam": {
                    "driver": "default",
                    "config": [{"subnet": "172.28.0.0/16"}]
                }
            }
        compose_content["networks"] = networks

        volumes = compose_content.get("volumes", {})
        volumes[volume_name] = None
        compose_content["volumes"] = volumes

        with open(COMPOSE_FILE, "w") as f:
            yaml.dump(compose_content, f, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        if BACKUP_COMPOSE_FILE.exists():
            shutil.copy2(BACKUP_COMPOSE_FILE, COMPOSE_FILE)
        raise Exception(f"Failed to add service to compose: {e}")


def create_instance_volume(name: str) -> str:
    instance_id = get_next_instance_id()
    volume_name = f"openclaw-{instance_id}-data"
    try:
        existing = CLIENT.volumes.get(volume_name) if hasattr(CLIENT.volumes, "get") else None
        if existing:
            return volume_name
    except Exception:
        pass
    try:
        volume = CLIENT.volumes.create(name=volume_name, driver="local")
        return volume.name
    except Exception:
        return volume_name


def start_compose_service(name: str) -> tuple[int, str, str]:
    returncode, stdout, stderr = run_docker_compose(
        ["docker-compose", "-f", str(COMPOSE_FILE), "up", "-d", name],
        cwd=str(COMPOSE_DIR)
    )
    return returncode, stdout, stderr


def sync_config_to_container(name: str, clear_first: bool = False) -> bool:
    import base64
    config_path = CONFIG_INSTANCES_DIR / name / "openclaw.json"
    if not config_path.exists():
        raise HTTPException(404, f"Config for {name} not found")

    config_content = config_path.read_text()
    encoded = base64.b64encode(config_content.encode()).decode()

    try:
        if clear_first:
            proc = subprocess.run(
                ["docker", "exec", name, "sh", "-c", "rm -rf /root/.openclaw/*"],
                capture_output=True, text=True
            )

        proc = subprocess.run(
            ["docker", "exec", name, "sh", "-c", f"echo {encoded} | base64 -d > /root/.openclaw/openclaw.json"],
            capture_output=True, text=True
        )
        if proc.returncode != 0:
            return False
        
        subprocess.run(
            ["docker", "exec", name, "sh", "-c", "chmod 644 /root/.openclaw/openclaw.json"],
            capture_output=True
        )
        
        return True
    except Exception:
        return False


def remove_service_from_compose(name: str) -> bool:
    backup_compose_file()
    try:
        if not COMPOSE_FILE.exists():
            return True
        with open(COMPOSE_FILE, "r") as f:
            compose_content = yaml.safe_load(f) or {}

        services = compose_content.get("services", {})
        volumes = compose_content.get("volumes", {})

        if name in services:
            service_volumes = services[name].get("volumes", [])
            for vol in service_volumes:
                if isinstance(vol, str) and ":" in vol:
                    vol_name = vol.split(":")[0]
                    if vol_name in volumes:
                        del volumes[vol_name]
            del services[name]

        with open(COMPOSE_FILE, "w") as f:
            yaml.dump(compose_content, f, default_flow_style=False, sort_keys=False)
        return True
    except Exception as e:
        if BACKUP_COMPOSE_FILE.exists():
            shutil.copy2(BACKUP_COMPOSE_FILE, COMPOSE_FILE)
        raise Exception(f"Failed to remove service from compose: {e}")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/instances")
async def list_instances():
    containers = get_nest_containers()
    admin_containers = {"nest-admin", "nest-admin-frontend"}
    instances = []
    running_names = {c["instance_id"] for c in containers if c["instance_id"] not in admin_containers}
    
    for c in containers:
        if c["instance_id"] in admin_containers:
            continue
        config_path = CONFIG_INSTANCES_DIR / c["instance_id"] / "openclaw.json"
        config = {}
        if config_path.exists():
            config = json.loads(config_path.read_text())
        instances.append({
            **c,
            "config": config,
            "config_exists": config_path.exists(),
        })
    
    if CONFIG_INSTANCES_DIR.exists():
        for d in CONFIG_INSTANCES_DIR.iterdir():
            if d.is_dir() and d.name not in running_names and d.name not in admin_containers:
                config_path = d / "openclaw.json"
                config = {}
                if config_path.exists():
                    config = json.loads(config_path.read_text())
                instances.append({
                    "name": d.name,
                    "status": "stopped",
                    "instance_id": d.name,
                    "image": "unknown",
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
    config = {}
    if config_path.exists():
        config = json.loads(config_path.read_text())
    
    container.reload()
    return {
        "name": container.name,
        "status": container.status,
        "image": container.image.tags[0] if container.image.tags else container.image.short_id,
        "instance_id": name,
        "config": config,
        "created": container.attrs.get("Created", "")[:19].replace("T", " "),
        "ports": container.ports,
    }


@app.post("/api/instances")
async def create_instance(data: InstanceCreateRequest):
    name = data.name
    if not name:
        raise HTTPException(400, "name is required")
    
    if not isinstance(name, str) or not name.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(400, "name must be alphanumeric with dashes/underscores only")
    
    instance_type = data.instance_type or "compose"
    gpu = data.gpu if data.gpu is not None else True
    
    image = data.image if data.image else "openclaw:pure-gpu" if gpu else "openclaw:pure-cpu"

    instance_dir = CONFIG_INSTANCES_DIR / name
    instance_dir.mkdir(parents=True, exist_ok=True)
    
    import secrets
    token = secrets.token_hex(16)
    
    default_config = {
        "logging": {
            "level": "info"
        },
        "models": {
            "mode": "merge",
            "providers": {
                "minimax": {
                    "baseUrl": "https://api.minimaxi.com/anthropic",
                    "api": "anthropic-messages",
                    "authHeader": True,
                    "models": [
                        {
                            "id": "MiniMax-M2.7-highspeed",
                            "name": "M2.7 超速版",
                            "reasoning": False,
                            "input": ["text"],
                            "cost": {"input": 15, "output": 60, "cacheRead": 2, "cacheWrite": 10},
                            "contextWindow": 200000,
                            "maxTokens": 8192
                        }
                    ]
                }
            }
        },
        "agents": {
            "defaults": {
                "model": {
                    "primary": "minimax/MiniMax-M2.7-highspeed"
                },
                "compaction": {
                    "mode": "safeguard"
                },
                "sandbox": {
                    "browser": {
                        "enabled": True,
                        "allowHostControl": True
                    }
                }
            }
        },
        "gateway": {
            "mode": "local",
            "bind": "lan",
            "trustedProxies": ["172.28.0.0/16", "127.0.0.0/8"],
            "controlUi": {
                "dangerouslyDisableDeviceAuth": True,
                "allowInsecureAuth": True,
                "allowedOrigins": [
                    "http://localhost:18789",
                    "http://127.0.0.1:18789",
                    "https://localhost:18443",
                    "https://192.168.2.118:18443"
                ]
            },
            "auth": {
                "mode": "token",
                "token": token
            }
        },
        "channels": {
            "telegram": {
                "enabled": True,
                "botToken": "",
                "dmPolicy": "open",
                "allowFrom": ["*"],
                "groupPolicy": "allowlist",
                "streaming": {
                    "mode": "partial"
                }
            },
            "feishu": {
                "enabled": True,
                "appId": "",
                "appSecret": "",
                "verificationToken": "",
                "allowFrom": ["*"]
            }
        },
        "plugins": {
            "allow": [],
            "entries": {}
        }
    }
    (instance_dir / "openclaw.json").write_text(json.dumps(default_config, indent=2))

    model = data.model or "minimax/MiniMax-M2.7-highspeed"
    if "/" in model:
        provider, model_id = model.split("/", 1)
    else:
        provider, model_id = "minimax", model

    api_key_to_use = data.apiKey

    if instance_type == "compose":
        ip = get_next_ip()
        http_port, app_port, data_port = get_next_ports()
        volume_name = create_instance_volume(name)
        add_service_to_compose(name, image, ip, http_port, app_port, data_port, api_key=api_key_to_use)
        returncode, stdout, stderr = start_compose_service(name)
        if returncode != 0:
            return {"name": name, "status": "created_with_errors", "compose_error": stderr}
        sync_config_to_container(name, clear_first=False)
        subprocess.run(["docker", "restart", name], capture_output=True)
        return {"name": name, "status": "created", "image": image, "ip": ip, "ports": {"http": http_port, "app": app_port, "data": data_port}}
    else:
        ip = get_next_ip()
        http_port, app_port, data_port = get_next_ports()
        volume_name = create_instance_volume(name)
        try:
            container = CLIENT.containers.run(
                image=image,
                name=name,
                detach=True,
                restart_policy="unless-stopped",
                mounts=[Mount(target="/root/.openclaw", source=volume_name, type="volume")],
                ports={
                    "18789/tcp": http_port,
                    "8070/tcp": app_port,
                    "11434/tcp": data_port
                },
                labels={
                    "openclaw.name": name,
                    "com.docker.compose.project": STACK_NAME
                }
            )
            import time
            time.sleep(2)
            sync_config_to_container(name, clear_first=False)
            subprocess.run(["docker", "restart", name], capture_output=True)
            return {"name": name, "status": "created", "image": image, "ip": ip, "ports": {"http": http_port, "app": app_port, "data": data_port}}
        except Exception as e:
            return {"name": name, "status": "creation_failed", "error": str(e)}


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
    
    try:
        remove_service_from_compose(name)
    except Exception:
        pass
    
    volume_name = f"nest_{name}_openclaw"
    try:
        volume = CLIENT.volumes.get(volume_name)
        volume.remove()
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
        raise HTTPException(404, f"Instance {name} not found")
    if container.status == "running":
        return {"name": name, "status": "already running"}
    container.start()
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


@app.post("/api/instances/{name}/sync-config")
async def sync_config(name: str):
    container = get_container_by_name(name)
    if not container:
        raise HTTPException(404, f"Instance {name} not found")
    
    config_path = CONFIG_INSTANCES_DIR / name / "openclaw.json"
    if not config_path.exists():
        raise HTTPException(404, f"Config for {name} not found")
    
    success = sync_config_to_container(name, clear_first=False)
    if not success:
        raise HTTPException(500, f"Failed to sync config to container {name}")
    
    try:
        container.exec_run("kill", "-HUP", "1")
    except Exception:
        pass
    
    return {"name": name, "status": "config_synced"}


@app.post("/api/instances/{name}/sync-config-volume")
async def sync_config_volume(name: str):
    container = get_container_by_name(name)
    if not container:
        raise HTTPException(404, f"Instance {name} not found")
    
    config_path = CONFIG_INSTANCES_DIR / name / "openclaw.json"
    if not config_path.exists():
        raise HTTPException(404, f"Config for {name} not found")
    
    success = sync_config_to_container(name, clear_first=True)
    if not success:
        raise HTTPException(500, f"Failed to sync config to container {name}")
    
    try:
        container.restart(timeout=10)
    except Exception:
        pass
    
    return {"name": name, "status": "config_volume_synced"}


@app.post("/api/stack/start")
async def start_stack():
    compose_file = COMPOSE_DIR / "docker-compose.yml"
    if not compose_file.exists():
        compose_file = Path("/app/compose/docker-compose.yml")
    if not compose_file.exists():
        raise HTTPException(404, "docker-compose.yml not found in /app/compose")
    
    returncode, stdout, stderr = run_docker_compose(
        ["docker-compose", "-f", str(compose_file), "up", "-d"],
        cwd=str(COMPOSE_DIR)
    )
    
    if returncode != 0:
        raise HTTPException(500, f"Failed to start stack: {stderr}")
    
    return {"status": "start requested", "output": stdout}


@app.post("/api/stack/stop")
async def stop_stack():
    compose_file = COMPOSE_DIR / "docker-compose.yml"
    if not compose_file.exists():
        compose_file = Path("/app/compose/docker-compose.yml")
    if not compose_file.exists():
        raise HTTPException(404, "docker-compose.yml not found in /app/compose")
    
    returncode, stdout, stderr = run_docker_compose(
        ["docker-compose", "-f", str(compose_file), "stop"],
        cwd=str(COMPOSE_DIR)
    )
    
    if returncode != 0:
        raise HTTPException(500, f"Failed to stop stack: {stderr}")
    
    return {"status": "stop requested", "output": stdout}


@app.get("/api/config/{name}")
async def get_config(name: str):
    if name == "base":
        config_path = CONFIG_BASE_DIR / "openclaw.json"
    else:
        config_path = CONFIG_INSTANCES_DIR / name / "openclaw.json"
    
    if not config_path.exists():
        raise HTTPException(404, f"Config for {name} not found")
    return json.loads(config_path.read_text())


@app.put("/api/config/{name}")
async def save_config(name: str, data: dict):
    if name == "base":
        instance_dir = CONFIG_BASE_DIR
    else:
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


@app.get("/api/base-config")
async def get_base_config():
    config_path = CONFIG_BASE_DIR / "openclaw.json"
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
