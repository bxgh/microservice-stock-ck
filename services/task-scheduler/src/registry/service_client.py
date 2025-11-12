"""
服务间通信客户端
提供服务发现后的HTTP客户端功能
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

import aiohttp
from .service_registry import get_service_registry, ServiceInstance

logger = logging.getLogger(__name__)


class ServiceClient:
    """服务间通信客户端"""

    def __init__(self, service_name: str, version: Optional[str] = None, tag: Optional[str] = None):
        self.service_name = service_name
        self.version = version
        self.tag = tag
        self.session: Optional[aiohttp.ClientSession] = None
        self.current_instance: Optional[ServiceInstance] = None
        self.registry = get_service_registry()

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.stop()

    async def start(self):
        """启动客户端"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            logger.info(f"Service client for {self.service_name} started")

    async def stop(self):
        """停止客户端"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info(f"Service client for {self.service_name} stopped")

    async def get_base_url(self) -> str:
        """
        获取服务的基础URL

        Returns:
            str: 服务基础URL
        """
        # 如果没有当前实例或实例不健康，重新发现
        if not self.current_instance:
            self.current_instance = await self.registry.get_service_instance(self.service_name, self.tag)

        if not self.current_instance:
            raise ConnectionError(f"No available instances found for service: {self.service_name}")

        return f"http://{self.current_instance.address}:{self.current_instance.port}"

    async def request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        发送HTTP请求到目标服务

        Args:
            method: HTTP方法
            path: 请求路径
            **kwargs: 其他请求参数

        Returns:
            Dict[str, Any]: 响应数据
        """
        max_retries = kwargs.pop('max_retries', 3)
        retry_delay = kwargs.pop('retry_delay', 1.0)

        for attempt in range(max_retries):
            try:
                base_url = await self.get_base_url()
                url = urljoin(base_url, path)

                if not self.session:
                    await self.start()

                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            logger.debug(f"Request to {self.service_name} successful: {method} {path}")
                            return data
                        except:
                            text = await response.text()
                            return {"status": "success", "data": text}
                    else:
                        error_text = await response.text()
                        logger.error(f"Request to {self.service_name} failed: {response.status} - {error_text}")

                        # 如果是服务不可用，清除当前实例
                        if response.status in [502, 503, 504]:
                            self.current_instance = None

                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=error_text
                        )

            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to request {self.service_name} after {max_retries} attempts: {e}")
                    raise

                logger.warning(f"Request to {self.service_name} failed (attempt {attempt + 1}): {e}, retrying...")
                self.current_instance = None  # 清除当前实例，下次重新发现
                await asyncio.sleep(retry_delay * (2 ** attempt))  # 指数退避

    async def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送GET请求"""
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送POST请求"""
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送PUT请求"""
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送DELETE请求"""
        return await self.request("DELETE", path, **kwargs)


class LoadBalancedServiceClient:
    """负载均衡服务客户端"""

    def __init__(self, service_name: str, strategy: str = "round_robin", tag: Optional[str] = None):
        self.service_name = service_name
        self.strategy = strategy
        self.tag = tag
        self.current_index = 0
        self.registry = get_service_registry()

    async def get_instances(self) -> List[ServiceInstance]:
        """获取所有可用实例"""
        return await self.registry.discover_service(self.service_name, self.tag)

    async def select_instance(self) -> Optional[ServiceInstance]:
        """
        根据策略选择实例

        Returns:
            Optional[ServiceInstance]: 选中的实例
        """
        instances = await self.get_instances()
        if not instances:
            return None

        if self.strategy == "round_robin":
            instance = instances[self.current_index % len(instances)]
            self.current_index += 1
            return instance
        elif self.strategy == "random":
            import random
            return random.choice(instances)
        elif self.strategy == "least_connections":
            # 简化实现：选择第一个实例
            # 实际应该根据连接数选择
            return instances[0]
        else:
            return instances[0]

    async def request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """
        发送负载均衡的HTTP请求

        Args:
            method: HTTP方法
            path: 请求路径
            **kwargs: 其他请求参数

        Returns:
            Dict[str, Any]: 响应数据
        """
        max_retries = kwargs.pop('max_retries', len(await self.get_instances()))

        for attempt in range(max_retries):
            instance = await self.select_instance()
            if not instance:
                raise ConnectionError(f"No available instances found for service: {self.service_name}")

            try:
                url = f"http://{instance.address}:{instance.port}/{path.lstrip('/')}"

                timeout = aiohttp.ClientTimeout(total=30)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.request(method, url, **kwargs) as response:
                        if response.status == 200:
                            try:
                                data = await response.json()
                                logger.debug(f"Request to {self.service_name} successful: {method} {path}")
                                return data
                            except:
                                text = await response.text()
                                return {"status": "success", "data": text}
                        else:
                            error_text = await response.text()
                            logger.error(f"Request to {self.service_name} failed: {response.status} - {error_text}")
                            raise aiohttp.ClientResponseError(
                                request_info=response.request_info,
                                history=response.history,
                                status=response.status,
                                message=error_text
                            )

            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to request {self.service_name} after trying all instances: {e}")
                    raise

                logger.warning(f"Request to instance {instance.service_id} failed: {e}, trying next instance...")

    async def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送GET请求"""
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送POST请求"""
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送PUT请求"""
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> Dict[str, Any]:
        """发送DELETE请求"""
        return await self.request("DELETE", path, **kwargs)


# 服务客户端工厂
class ServiceClientFactory:
    """服务客户端工厂"""

    _clients: Dict[str, ServiceClient] = {}

    @classmethod
    def get_client(cls, service_name: str, **kwargs) -> ServiceClient:
        """
        获取服务客户端实例

        Args:
            service_name: 服务名称
            **kwargs: 客户端参数

        Returns:
            ServiceClient: 服务客户端实例
        """
        key = f"{service_name}:{kwargs.get('version', '')}:{kwargs.get('tag', '')}"

        if key not in cls._clients:
            cls._clients[key] = ServiceClient(service_name, **kwargs)

        return cls._clients[key]

    @classmethod
    def get_load_balanced_client(cls, service_name: str, **kwargs) -> LoadBalancedServiceClient:
        """
        获取负载均衡服务客户端实例

        Args:
            service_name: 服务名称
            **kwargs: 客户端参数

        Returns:
            LoadBalancedServiceClient: 负载均衡服务客户端实例
        """
        key = f"lb:{service_name}:{kwargs.get('strategy', 'round_robin')}:{kwargs.get('tag', '')}"

        if key not in cls._clients:
            cls._clients[key] = LoadBalancedServiceClient(service_name, **kwargs)

        return cls._clients[key]

    @classmethod
    async def close_all(cls):
        """关闭所有客户端"""
        for client in cls._clients.values():
            await client.stop()
        cls._clients.clear()