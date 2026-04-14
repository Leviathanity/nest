import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional

import docker
from docker.models.containers import Container

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebhookClient:
    def __init__(self, webhook_url: Optional[str]):
        self.webhook_url = webhook_url
        self.enabled = bool(webhook_url)

    async def send(self, event_type: str, data: dict) -> bool:
        if not self.enabled:
            return True

        payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status < 400:
                        logger.info(f"Webhook sent successfully: {event_type}")
                        return True
                    else:
                        logger.error(f"Webhook failed: {resp.status}")
                        return False
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return False


class InstanceMonitor:
    def __init__(self, container: Container, webhook: WebhookClient):
        self.container = container
        self.webhook = webhook
        self.name = container.name
        self.instance_id = self._get_instance_id()
        self.last_status = None
        self.last_health_status = None

    def _get_instance_id(self) -> str:
        labels = self.container.labels
        return labels.get('openclaw.instance', 'unknown')

    def _get_instance_config(self) -> dict:
        labels = self.container.labels
        return {
            "instanceId": self.instance_id,
            "instanceName": self.name,
            "image": self.container.image.tags[0] if self.container.image.tags else "unknown",
            "created": self.container.attrs.get('Created', 'unknown'),
            "labels": labels
        }

    async def check_status(self) -> dict:
        try:
            self.container.reload()
            status = self.container.status
            health_status = None

            if self.container.attrs.get('State', {}).get('Health'):
                health_status = self.container.attrs['State']['Health'].get('Status')

            info = {
                **self._get_instance_config(),
                "status": status,
                "healthStatus": health_status,
                "ports": self.container.ports,
                "uptime": self._get_uptime()
            }

            # 检测状态变化
            if self.last_status != status:
                await self._on_status_change(status)
                self.last_status = status

            if self.last_health_status != health_status:
                await self._on_health_change(health_status)
                self.last_health_status = health_status

            return info

        except Exception as e:
            logger.error(f"Failed to check status for {self.name}: {e}")
            return {
                "instanceName": self.name,
                "instanceId": self.instance_id,
                "error": str(e)
            }

    def _get_uptime(self) -> Optional[str]:
        try:
            started = self.container.attrs.get('State', {}).get('StartedAt')
            if started:
                from datetime import datetime
                started_time = datetime.fromisoformat(started.replace('Z', '+00:00'))
                delta = datetime.now(started_time.tzinfo) - started_time
                return str(delta).split('.')[0]
        except:
            pass
        return None

    async def _on_status_change(self, new_status: str):
        logger.info(f"[{self.name}] Status changed to: {new_status}")

        event = {
            "instance": self._get_instance_config(),
            "previousStatus": self.last_status,
            "newStatus": new_status,
            "message": f"实例 {self.name} 状态变更为 {new_status}"
        }

        if new_status == "exited":
            exit_code = self.container.attrs.get('State', {}).get('ExitCode', 0)
            event["exitCode"] = exit_code
            event["errorLogs"] = await self._get_error_logs()
            await self.webhook.send("instance.crashed", event)
        elif new_status == "running":
            await self.webhook.send("instance.started", event)

    async def _on_health_change(self, new_health: Optional[str]):
        if new_health == "unhealthy":
            event = {
                "instance": self._get_instance_config(),
                "healthStatus": new_health,
                "message": f"实例 {self.name} 健康检查失败"
            }
            await self.webhook.send("instance.unhealthy", event)

    async def _get_error_logs(self) -> list:
        try:
            logs = self.container.logs(tail=100, stdout=True, stderr=True, timestamps=True)
            lines = logs.decode('utf-8', errors='ignore').split('\n')
            error_lines = [l for l in lines if 'error' in l.lower() or 'exception' in l.lower() or 'fail' in l.lower()]
            return error_lines[-20:]
        except:
            return []


class ClusterMonitor:
    def __init__(self):
        self.client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
        self.webhook = WebhookClient(os.getenv('WEBHOOK_URL'))
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '10'))
        self.instance_monitors: dict[str, InstanceMonitor] = {}
        self._running = False

    def discover_instances(self):
        containers = self.client.containers.list(
            all=True,
            filters={"label": ["openclaw.cluster=enabled"]}
        )

        current_names = set()
        for container in containers:
            current_names.add(container.name)
            if container.name not in self.instance_monitors:
                logger.info(f"Discovered new instance: {container.name}")
                self.instance_monitors[container.name] = InstanceMonitor(container, self.webhook)

        # 移除已删除的实例
        removed = set(self.instance_monitors.keys()) - current_names
        for name in removed:
            del self.instance_monitors[name]
            logger.info(f"Instance removed: {name}")

    async def check_all(self) -> list[dict]:
        tasks = [m.check_status() for m in self.instance_monitors.values()]
        return await asyncio.gather(*tasks)

    async def run(self):
        self._running = True
        logger.info("Cluster Monitor started")

        while self._running:
            try:
                self.discover_instances()
                results = await self.check_all()

                # 保存状态快照
                self._save_snapshot(results)

            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

            await asyncio.sleep(self.check_interval)

    def _save_snapshot(self, results: list):
        try:
            os.makedirs('/app/data', exist_ok=True)
            with open('/app/data/status.json', 'w') as f:
                json.dump({
                    "timestamp": datetime.utcnow().isoformat(),
                    "instances": results
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")

    def stop(self):
        self._running = False
        logger.info("Cluster Monitor stopped")


async def main():
    monitor = ClusterMonitor()

    try:
        await monitor.run()
    except KeyboardInterrupt:
        monitor.stop()


if __name__ == "__main__":
    asyncio.run(main())
