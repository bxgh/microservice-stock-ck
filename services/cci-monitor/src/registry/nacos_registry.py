import asyncio
import contextlib
import json
import socket
import aiohttp
from ..config.settings import settings
from ..core.logger import cci_logger as logger

class NacosRegistry:
    """Nacos服务注册类"""

    def __init__(self, nacos_url: str):
        self.nacos_url = nacos_url
        self.session = None

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            use_dns_cache=False,
            family=socket.AF_INET,
            ssl=False
        )
        self.session = aiohttp.ClientSession(
            connector=connector,
            trust_env=False
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def register_service(self, service_config: dict) -> bool:
        """注册服务到Nacos"""
        try:
            url = f"{self.nacos_url}/nacos/v1/ns/instance"
            params = {}
            for key, value in service_config.items():
                if key == 'metadata' and isinstance(value, dict):
                    params[key] = json.dumps(value)
                elif isinstance(value, bool):
                    params[key] = str(value).lower()
                else:
                    params[key] = str(value)

            async with self.session.post(url, params=params) as response:
                if response.status == 200:
                    result = await response.text()
                    if result == "ok":
                        logger.info(f"✅ 服务注册成功: {service_config.get('serviceName')}")
                        return True
                logger.error(f"❌ 服务注册失败: {response.status} - {await response.text()}")
                return False
        except Exception as e:
            logger.error(f"❌ 服务注册异常: {e}")
            return False

    async def send_heartbeat(self, service_config: dict) -> bool:
        """发送心跳到Nacos"""
        try:
            url = f"{self.nacos_url}/nacos/v1/ns/instance/beat"
            params = {
                "serviceName": service_config["serviceName"],
                "ip": service_config["ip"],
                "port": service_config["port"],
                "groupName": service_config.get("groupName", "DEFAULT_GROUP"),
                "clusterName": service_config.get("clusterName", "DEFAULT"),
                "namespaceId": service_config.get("namespaceId", ""),
                "beat": json.dumps({
                    "cluster": service_config.get("clusterName", "DEFAULT"),
                    "ip": service_config["ip"],
                    "port": service_config["port"],
                    "metadata": service_config.get("metadata", {}),
                    "scheduled": True,
                    "instanceId": f"{service_config['ip']}#{service_config['port']}#{service_config.get('clusterName', 'DEFAULT')}#{service_config.get('groupName', 'DEFAULT_GROUP')}@@{service_config['serviceName']}",
                    "weight": service_config.get("weight", 1.0),
                    "healthy": True,
                    "enabled": True,
                    "ephemeral": True,
                    "instanceHeartBeatInterval": 5000,
                    "instanceHeartBeatTimeOut": 15000
                })
            }

            async with self.session.put(url, params=params) as response:
                if response.status == 200:
                    result = await response.text()
                    if result and result != "":
                        return True
                return False
        except Exception as e:
            return False

def get_local_ip() -> str:
    """获取本地IP地址"""
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if local_ip.startswith("172.") or local_ip.startswith("192.168.") or local_ip.startswith("10."):
            return local_ip
    except Exception:
        pass
    return "127.0.0.1"

nacos_registry = None
heartbeat_task = None
service_config_global = None

async def heartbeat_task_func(heartbeat_interval: int = 10):
    global nacos_registry, service_config_global
    while True:
        try:
            if nacos_registry and service_config_global:
                async with nacos_registry:
                    await nacos_registry.send_heartbeat(service_config_global)
            await asyncio.sleep(heartbeat_interval)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(heartbeat_interval)

async def register_to_nacos():
    if not settings.ENABLE_NACOS:
        return True

    global nacos_registry, service_config_global, heartbeat_task
    nacos_registry = NacosRegistry(settings.NACOS_SERVER_URL)
    local_ip = get_local_ip()
    
    service_config_global = {
        "serviceName": settings.NAME.lower(),
        "ip": local_ip,
        "port": settings.PORT,
        "groupName": settings.NACOS_GROUP,
        "namespaceId": settings.NACOS_NAMESPACE,
        "metadata": {
            "version": settings.VERSION,
            "env": settings.ENV,
            "description": "CCI Monitor System"
        }
    }

    async with nacos_registry:
        success = await nacos_registry.register_service(service_config_global)
        if success:
            if heartbeat_task is None:
                heartbeat_task = asyncio.create_task(heartbeat_task_func())
            return True
    return False

async def cleanup_nacos():
    global heartbeat_task
    if heartbeat_task:
        heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task
        heartbeat_task = None
