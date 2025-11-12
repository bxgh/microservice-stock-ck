"""
Nacos 服务注册发现客户端
使用官方Python SDK实现
"""

import asyncio
import json
import logging
import socket
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import aiohttp
from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class NacosServiceInstance:
    """Nacos服务实例信息"""
    service_name: str
    ip: str
    port: int
    cluster_name: str = "DEFAULT"
    group_name: str = "DEFAULT_GROUP"
    metadata: Dict[str, str] = None
    weight: float = 1.0
    enabled: bool = True
    healthy: bool = True
    ephemeral: bool = True

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class NacosRegistry:
    """Nacos服务注册发现客户端"""

    def __init__(self, nacos_url: str = "http://localhost:8848"):
        self.nacos_url = nacos_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.local_service_id: Optional[str] = None
        self.heartbeat_task: Optional[asyncio.Task] = None

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.stop()

    async def start(self):
        """启动Nacos客户端"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=10)
            # 创建连接器，禁用代理
            connector = aiohttp.TCPConnector(
                use_dns_cache=False,
                family=0,
                ssl=False
            )
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                trust_env=True  # 信任环境变量但会尝试绕过代理
            )
            logger.info("Nacos registry client started")

    async def stop(self):
        """停止Nacos客户端"""
        # 注销服务
        if self.local_service_id:
            await self.deregister_service()

        # 取消心跳任务
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        # 关闭会话
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Nacos registry client stopped")

    async def register_service(self, service: NacosServiceInstance) -> bool:
        """
        注册服务到Nacos

        Args:
            service: Nacos服务实例

        Returns:
            bool: 注册是否成功
        """
        try:
            if not self.session:
                await self.start()

            # 构建注册请求
            payload = {
                "serviceName": service.service_name,
                "ip": service.ip,
                "port": service.port,
                "clusterName": service.cluster_name,
                "groupName": service.group_name,
                "metadata": json.dumps(service.metadata) if service.metadata else "{}",
                "weight": service.weight,
                "enabled": "true" if service.enabled else "false",
                "healthy": "true" if service.healthy else "false",
                "ephemeral": "true" if service.ephemeral else "false"
            }

            url = f"{self.nacos_url}/nacos/v1/ns/instance"

            async with self.session.post(url, params=payload) as response:
                if response.status == 200:
                    result = await response.text()
                    if result == "ok":
                        self.local_service_id = f"{service.service_name}#{service.ip}:{service.port}"
                        logger.info(f"Service registered successfully: {self.local_service_id}")

                        # 启动心跳检查
                        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop(service))
                        return True
                    else:
                        logger.error(f"Failed to register service: {result}")
                        return False
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to register service: {response.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"Error registering service: {e}")
            return False

    async def deregister_service(self, service: Optional[NacosServiceInstance] = None) -> bool:
        """
        从Nacos注销服务

        Args:
            service: 服务实例，如果为空则使用本地注册的服务

        Returns:
            bool: 注销是否成功
        """
        try:
            if not service and self.local_service_id:
                # 从local_service_id解析服务信息
                service_info = self.local_service_id.split('#')
                if len(service_info) == 2:
                    service_name = service_info[0]
                    ip_port = service_info[1].split(':')
                    if len(ip_port) == 2:
                        service = NacosServiceInstance(
                            service_name=service_name,
                            ip=ip_port[0],
                            port=int(ip_port[1])
                        )

            if not service:
                logger.warning("No service provided for deregistration")
                return False

            if not self.session:
                await self.start()

            url = f"{self.nacos_url}/nacos/v1/ns/instance"

            params = {
                "serviceName": service.service_name,
                "ip": service.ip,
                "port": service.port,
                "clusterName": service.cluster_name,
                "groupName": service.group_name,
                "ephemeral": "true"
            }

            async with self.session.delete(url, params=params) as response:
                if response.status == 200:
                    result = await response.text()
                    if result == "ok":
                        logger.info(f"Service deregistered successfully: {self.local_service_id}")
                        self.local_service_id = None
                        return True
                    else:
                        logger.error(f"Failed to deregister service: {result}")
                        return False
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to deregister service: {response.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"Error deregistering service: {e}")
            return False

    async def discover_service(self, service_name: str, group_name: str = "DEFAULT_GROUP") -> List[NacosServiceInstance]:
        """
        发现服务实例

        Args:
            service_name: 服务名称
            group_name: 分组名称

        Returns:
            List[NacosServiceInstance]: 服务实例列表
        """
        try:
            if not self.session:
                await self.start()

            url = f"{self.nacos_url}/nacos/v1/ns/instance/list"

            params = {
                "serviceName": service_name,
                "groupName": group_name
            }

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    instances = []

                    for host in data.get("hosts", []):
                        instance = NacosServiceInstance(
                            service_name=service_name,
                            ip=host.get("ip"),
                            port=host.get("port"),
                            cluster_name=host.get("clusterName", "DEFAULT"),
                            group_name=group_name,
                            metadata=host.get("metadata", {}),
                            weight=host.get("weight", 1.0),
                            enabled=host.get("enabled", True),
                            healthy=host.get("healthy", True),
                            ephemeral=host.get("ephemeral", True)
                        )
                        instances.append(instance)

                    logger.info(f"Discovered {len(instances)} instances for service: {service_name}")
                    return instances
                else:
                    logger.error(f"Failed to discover service: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error discovering service: {e}")
            return []

    async def get_service_instance(self, service_name: str, group_name: str = "DEFAULT_GROUP") -> Optional[NacosServiceInstance]:
        """
        获取单个服务实例（负载均衡）

        Args:
            service_name: 服务名称
            group_name: 分组名称

        Returns:
            Optional[NacosServiceInstance]: 随机选择的服务实例
        """
        services = await self.discover_service(service_name, group_name)
        if not services:
            return None

        # 简单的随机选择算法
        import random
        return random.choice(services)

    async def list_services(self) -> Dict[str, List[NacosServiceInstance]]:
        """
        列出所有注册的服务

        Returns:
            Dict[str, List[NacosServiceInstance]]: 服务名称到实例列表的映射
        """
        try:
            if not self.session:
                await self.start()

            url = f"{self.nacos_url}/nacos/v1/ns/service/list"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    services_by_name = {}

                    for service_name in data.get("doms", []):
                        instances = await self.discover_service(service_name)
                        services_by_name[service_name] = instances

                    return services_by_name
                else:
                    logger.error(f"Failed to list services: {response.status}")
                    return {}

        except Exception as e:
            logger.error(f"Error listing services: {e}")
            return {}

    async def _heartbeat_loop(self, service: NacosServiceInstance):
        """
        心跳检查循环

        Args:
            service: 服务实例信息
        """
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒发送一次心跳

                # 发送心跳
                success = await self._send_heartbeat(service)
                if success:
                    logger.debug(f"Heartbeat sent successfully for service: {service.service_name}")
                else:
                    logger.warning(f"Heartbeat failed for service: {service.service_name}")

            except asyncio.CancelledError:
                logger.info("Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)  # 错误后短暂等待

    async def _send_heartbeat(self, service: NacosServiceInstance) -> bool:
        """
        发送心跳到Nacos

        Args:
            service: 服务实例

        Returns:
            bool: 心跳是否成功
        """
        try:
            if not self.session:
                await self.start()

            url = f"{self.nacos_url}/nacos/v1/ns/instance/beat"

            params = {
                "serviceName": service.service_name,
                "ip": service.ip,
                "port": service.port,
                "clusterName": service.cluster_name,
                "groupName": service.group_name,
                "ephemeral": "true"
            }

            async with self.session.put(url, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("code") == 10200  # 10200表示心跳成功
                else:
                    logger.error(f"Heartbeat failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            return False

    def get_local_ip(self) -> str:
        """
        获取本机IP地址

        Returns:
            str: 本机IP地址
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"


# 全局Nacos注册实例
_nacos_registry: Optional[NacosRegistry] = None


def get_nacos_registry() -> NacosRegistry:
    """
    获取全局Nacos注册实例

    Returns:
        NacosRegistry: Nacos注册实例
    """
    global _nacos_registry
    if _nacos_registry is None:
        _nacos_registry = NacosRegistry()
    return _nacos_registry


async def init_nacos_registry(nacos_url: str = "http://localhost:8848") -> NacosRegistry:
    """
    初始化Nacos注册中心

    Args:
        nacos_url: Nacos地址

    Returns:
        NacosRegistry: Nacos注册实例
    """
    global _nacos_registry
    if _nacos_registry is None:
        _nacos_registry = NacosRegistry(nacos_url)
    await _nacos_registry.start()
    return _nacos_registry