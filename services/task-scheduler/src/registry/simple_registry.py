"""
轻量级HTTP服务注册发现
简单实现，无需外部依赖
"""

import asyncio
import json
import logging
import socket
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import aiohttp
from aiohttp import web

logger = logging.getLogger(__name__)


@dataclass
class SimpleServiceInstance:
    """简单服务实例信息"""
    service_id: str
    service_name: str
    host: str
    port: int
    tags: List[str]
    metadata: Dict[str, str]
    health_check_url: str
    last_heartbeat: float


class SimpleServiceRegistry:
    """简单的服务注册中心（内存存储）"""

    def __init__(self, registry_port: int = 8501):
        self.registry_port = registry_port
        self.services: Dict[str, SimpleServiceInstance] = {}
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None

    async def start_registry(self):
        """启动注册中心HTTP服务"""
        try:
            self.app = web.Application()
            self.app.add_routes([
                web.post('/register', self.register_handler),
                web.delete('/deregister/{service_id}', self.deregister_handler),
                web.get('/discover/{service_name}', self.discover_handler),
                web.get('/services', self.list_services_handler),
                web.get('/health', self.health_handler)
            ])

            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, '0.0.0.0', self.registry_port)
            await self.site.start()

            logger.info(f"Simple registry started on port {self.registry_port}")

        except Exception as e:
            logger.error(f"Failed to start registry: {e}")
            raise

    async def stop_registry(self):
        """停止注册中心服务"""
        try:
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
            logger.info("Simple registry stopped")
        except Exception as e:
            logger.error(f"Error stopping registry: {e}")

    async def register_handler(self, request: web.Request) -> web.Response:
        """处理服务注册请求"""
        try:
            data = await request.json()

            instance = SimpleServiceInstance(
                service_id=data['service_id'],
                service_name=data['service_name'],
                host=data['host'],
                port=data['port'],
                tags=data.get('tags', []),
                metadata=data.get('metadata', {}),
                health_check_url=data['health_check_url'],
                last_heartbeat=time.time()
            )

            self.services[instance.service_id] = instance
            logger.info(f"Service registered: {instance.service_id}")

            return web.json_response({'status': 'success', 'message': 'Service registered'})

        except Exception as e:
            logger.error(f"Registration error: {e}")
            return web.json_response({'status': 'error', 'message': str(e)}, status=400)

    async def deregister_handler(self, request: web.Request) -> web.Response:
        """处理服务注销请求"""
        try:
            service_id = request.match_info['service_id']

            if service_id in self.services:
                del self.services[service_id]
                logger.info(f"Service deregistered: {service_id}")
                return web.json_response({'status': 'success', 'message': 'Service deregistered'})
            else:
                return web.json_response({'status': 'error', 'message': 'Service not found'}, status=404)

        except Exception as e:
            logger.error(f"Deregistration error: {e}")
            return web.json_response({'status': 'error', 'message': str(e)}, status=400)

    async def discover_handler(self, request: web.Request) -> web.Response:
        """处理服务发现请求"""
        try:
            service_name = request.match_info['service_name']

            instances = [
                asdict(instance) for instance in self.services.values()
                if instance.service_name == service_name
            ]

            return web.json_response({
                'service_name': service_name,
                'instances': instances,
                'count': len(instances)
            })

        except Exception as e:
            logger.error(f"Discovery error: {e}")
            return web.json_response({'status': 'error', 'message': str(e)}, status=400)

    async def list_services_handler(self, request: web.Request) -> web.Response:
        """列出所有服务"""
        try:
            services_by_name = {}
            for instance in self.services.values():
                if instance.service_name not in services_by_name:
                    services_by_name[instance.service_name] = []
                services_by_name[instance.service_name].append(asdict(instance))

            return web.json_response({
                'services': services_by_name,
                'total_services': len(services_by_name),
                'total_instances': len(self.services)
            })

        except Exception as e:
            logger.error(f"List services error: {e}")
            return web.json_response({'status': 'error', 'message': str(e)}, status=400)

    async def health_handler(self, request: web.Request) -> web.Response:
        """健康检查"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services_count': len(self.services)
        })


class SimpleServiceClient:
    """简单服务客户端"""

    def __init__(self, registry_url: str = f"http://localhost:8501"):
        self.registry_url = registry_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def start(self):
        """启动客户端"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def stop(self):
        """停止客户端"""
        if self.session:
            await self.session.close()
            self.session = None

    async def register_service(self, instance: SimpleServiceInstance) -> bool:
        """注册服务"""
        try:
            if not self.session:
                await self.start()

            url = f"{self.registry_url}/register"
            data = asdict(instance)

            async with self.session.post(url, json=data) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"Register service error: {e}")
            return False

    async def deregister_service(self, service_id: str) -> bool:
        """注销服务"""
        try:
            if not self.session:
                await self.start()

            url = f"{self.registry_url}/deregister/{service_id}"

            async with self.session.delete(url) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"Deregister service error: {e}")
            return False

    async def discover_service(self, service_name: str) -> List[SimpleServiceInstance]:
        """发现服务"""
        try:
            if not self.session:
                await self.start()

            url = f"{self.registry_url}/discover/{service_name}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    instances = []
                    for instance_data in data['instances']:
                        instance = SimpleServiceInstance(
                            service_id=instance_data['service_id'],
                            service_name=instance_data['service_name'],
                            host=instance_data['host'],
                            port=instance_data['port'],
                            tags=instance_data['tags'],
                            metadata=instance_data['metadata'],
                            health_check_url=instance_data['health_check_url'],
                            last_heartbeat=instance_data['last_heartbeat']
                        )
                        instances.append(instance)
                    return instances
                else:
                    return []

        except Exception as e:
            logger.error(f"Discover service error: {e}")
            return []

    async def get_service_instance(self, service_name: str) -> Optional[SimpleServiceInstance]:
        """获取单个服务实例"""
        instances = await self.discover_service(service_name)
        if instances:
            return instances[0]  # 简单返回第一个实例
        return None

    def get_local_ip(self) -> str:
        """获取本机IP"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"


# 全局简单注册中心实例
_simple_registry: Optional[SimpleServiceRegistry] = None
_simple_client: Optional[SimpleServiceClient] = None


def get_simple_registry() -> SimpleServiceRegistry:
    """获取简单注册中心实例"""
    global _simple_registry
    if _simple_registry is None:
        _simple_registry = SimpleServiceRegistry()
    return _simple_registry


def get_simple_client() -> SimpleServiceClient:
    """获取简单客户端实例"""
    global _simple_client
    if _simple_client is None:
        _simple_client = SimpleServiceClient()
    return _simple_client