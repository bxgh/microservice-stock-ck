"""
服务注册发现模块
提供 Consul 服务注册和发现功能
"""

import asyncio
import json
import logging
import socket
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import aiohttp
from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class ServiceInstance:
    """服务实例信息"""
    service_id: str
    service_name: str
    address: str
    port: int
    tags: List[str]
    meta: Dict[str, str]
    health_check_url: str
    health_check_interval: str = "10s"
    health_check_timeout: str = "5s"


class ServiceRegistry:
    """服务注册发现客户端"""

    def __init__(self, consul_url: str = "http://localhost:8500"):
        self.consul_url = consul_url
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
        """启动服务注册客户端"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info("Service registry client started")

    async def stop(self):
        """停止服务注册客户端"""
        # 取消注册
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
            logger.info("Service registry client stopped")

    async def register_service(self, service: ServiceInstance) -> bool:
        """
        注册服务到 Consul

        Args:
            service: 服务实例信息

        Returns:
            bool: 注册是否成功
        """
        try:
            if not self.session:
                await self.start()

            # 构建注册请求
            payload = {
                "ID": service.service_id,
                "Name": service.service_name,
                "Address": service.address,
                "Port": service.port,
                "Tags": service.tags,
                "Meta": service.meta,
                "EnableTagOverride": False,
                "Check": {
                    "HTTP": service.health_check_url,
                    "Interval": service.health_check_interval,
                    "Timeout": service.health_check_timeout,
                    "DeregisterCriticalServiceAfter": "30s"
                }
            }

            url = f"{self.consul_url}/v1/agent/service/register"

            async with self.session.put(url, json=payload) as response:
                if response.status == 200:
                    self.local_service_id = service.service_id
                    logger.info(f"Service registered successfully: {service.service_id}")

                    # 启动心跳检查
                    self.heartbeat_task = asyncio.create_task(self._heartbeat_loop(service))
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to register service: {response.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"Error registering service: {e}")
            return False

    async def deregister_service(self, service_id: Optional[str] = None) -> bool:
        """
        从 Consul 注销服务

        Args:
            service_id: 服务ID，如果不提供则使用本地注册的ID

        Returns:
            bool: 注销是否成功
        """
        try:
            target_service_id = service_id or self.local_service_id
            if not target_service_id:
                logger.warning("No service ID provided for deregistration")
                return False

            if not self.session:
                await self.start()

            url = f"{self.consul_url}/v1/agent/service/deregister/{target_service_id}"

            async with self.session.put(url) as response:
                if response.status == 200:
                    logger.info(f"Service deregistered successfully: {target_service_id}")
                    self.local_service_id = None
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to deregister service: {response.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"Error deregistering service: {e}")
            return False

    async def discover_service(self, service_name: str, tag: Optional[str] = None) -> List[ServiceInstance]:
        """
        发现服务实例

        Args:
            service_name: 服务名称
            tag: 服务标签过滤

        Returns:
            List[ServiceInstance]: 服务实例列表
        """
        try:
            if not self.session:
                await self.start()

            # 构建查询URL
            url = f"{self.consul_url}/v1/health/service/{service_name}?passing=true"
            if tag:
                url += f"&tag={tag}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    services_data = await response.json()
                    services = []

                    for service_data in services_data:
                        service_info = service_data["Service"]
                        service = ServiceInstance(
                            service_id=service_info["ID"],
                            service_name=service_info["Service"],
                            address=service_info["Address"],
                            port=service_info["Port"],
                            tags=service_info.get("Tags", []),
                            meta=service_info.get("Meta", {}),
                            health_check_url="",  # 健康检查信息不在此处
                            health_check_interval="10s",
                            health_check_timeout="5s"
                        )
                        services.append(service)

                    logger.info(f"Discovered {len(services)} instances for service: {service_name}")
                    return services
                else:
                    logger.error(f"Failed to discover service: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error discovering service: {e}")
            return []

    async def get_service_instance(self, service_name: str, tag: Optional[str] = None) -> Optional[ServiceInstance]:
        """
        获取单个服务实例（负载均衡）

        Args:
            service_name: 服务名称
            tag: 服务标签过滤

        Returns:
            Optional[ServiceInstance]: 随机选择的服务实例
        """
        services = await self.discover_service(service_name, tag)
        if not services:
            return None

        # 简单的随机选择算法（可替换为更复杂的负载均衡策略）
        import random
        return random.choice(services)

    async def list_services(self) -> Dict[str, List[ServiceInstance]]:
        """
        列出所有注册的服务

        Returns:
            Dict[str, List[ServiceInstance]]: 服务名称到实例列表的映射
        """
        try:
            if not self.session:
                await self.start()

            url = f"{self.consul_url}/v1/agent/services"

            async with self.session.get(url) as response:
                if response.status == 200:
                    services_data = await response.json()
                    services_by_name = {}

                    for service_id, service_info in services_data.items():
                        service = ServiceInstance(
                            service_id=service_id,
                            service_name=service_info["Service"],
                            address=service_info["Address"],
                            port=service_info["Port"],
                            tags=service_info.get("Tags", []),
                            meta=service_info.get("Meta", {}),
                            health_check_url="",
                            health_check_interval="10s",
                            health_check_timeout="5s"
                        )

                        if service.service_name not in services_by_name:
                            services_by_name[service.service_name] = []
                        services_by_name[service.service_name].append(service)

                    return services_by_name
                else:
                    logger.error(f"Failed to list services: {response.status}")
                    return {}

        except Exception as e:
            logger.error(f"Error listing services: {e}")
            return {}

    async def _heartbeat_loop(self, service: ServiceInstance):
        """
        心跳检查循环

        Args:
            service: 服务实例信息
        """
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒检查一次

                # 检查Consul连接
                if await self._check_consul_health():
                    logger.debug(f"Heartbeat check passed for service: {service.service_id}")
                else:
                    logger.warning(f"Heartbeat check failed for service: {service.service_id}")

            except asyncio.CancelledError:
                logger.info("Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)  # 错误后短暂等待

    async def _check_consul_health(self) -> bool:
        """
        检查 Consul 健康状态

        Returns:
            bool: Consul 是否健康
        """
        try:
            if not self.session:
                await self.start()

            url = f"{self.consul_url}/v1/status/leader"

            async with self.session.get(url) as response:
                return response.status == 200 and await response.text() != ""

        except Exception as e:
            logger.error(f"Consul health check failed: {e}")
            return False

    def get_local_ip(self) -> str:
        """
        获取本机IP地址

        Returns:
            str: 本机IP地址
        """
        try:
            # 创建UDP socket连接到外部地址来获取本地IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"


# 全局服务注册实例
_service_registry: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    """
    获取全局服务注册实例

    Returns:
        ServiceRegistry: 服务注册实例
    """
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry()
    return _service_registry


async def init_service_registry(consul_url: str = "http://localhost:8500") -> ServiceRegistry:
    """
    初始化服务注册中心

    Args:
        consul_url: Consul 地址

    Returns:
        ServiceRegistry: 服务注册实例
    """
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry(consul_url)
    await _service_registry.start()
    return _service_registry