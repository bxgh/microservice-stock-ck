#!/usr/bin/env python3
"""
Nacos 服务注册模板
可直接复制到其他微服务中使用，实现标准化的 Nacos 服务注册发现
"""

import asyncio
import json
import logging
import os
import socket
from typing import Dict, Optional

import aiohttp

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 全局变量
nacos_registry = None
heartbeat_task = None
service_config = None


class NacosRegistry:
    """Nacos服务注册类 - 可直接复用"""

    def __init__(self, nacos_url: str):
        self.nacos_url = nacos_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
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
                        logger.debug(f"💓 心跳发送成功: {service_config.get('serviceName')}")
                        return True
                logger.warning(f"⚠️ 心跳发送失败: {response.status} - {await response.text()}")
                return False
        except Exception as e:
            logger.debug(f"❌ 心跳发送异常: {e}")
            return False


def get_local_ip() -> str:
    """获取本地IP地址 - 容器优化版"""
    # 在Docker容器环境中，优先获取容器内部网络IP
    try:
        # 尝试获取主机名对应的IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if local_ip.startswith("172.") or local_ip.startswith("192.168.") or local_ip.startswith("10."):
            return local_ip
    except:
        pass

    # 回退到原始方法
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


async def heartbeat_task_func(heartbeat_interval: int = 10):
    """心跳任务函数"""
    global nacos_registry, service_config

    while True:
        try:
            if nacos_registry and service_config:
                async with nacos_registry:
                    await nacos_registry.send_heartbeat(service_config)
            await asyncio.sleep(heartbeat_interval)
        except asyncio.CancelledError:
            logger.info("🛑 心跳任务已取消")
            break
        except Exception as e:
            logger.error(f"❌ 心跳任务异常: {e}")
            await asyncio.sleep(heartbeat_interval)


async def register_to_nacos(service_name: str, service_port: int,
                           framework: str, description: str,
                           additional_metadata: Optional[Dict] = None,
                           max_retries: int = 3, retry_delay: int = 5,
                           heartbeat_interval: int = 10) -> bool:
    """
    注册服务到Nacos - 通用接口

    Args:
        service_name: 服务名称
        service_port: 服务端口
        framework: 框架名称
        description: 服务描述
        additional_metadata: 额外的元数据
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        heartbeat_interval: 心跳间隔（秒）

    Returns:
        bool: 注册是否成功
    """
    global nacos_registry, service_config, heartbeat_task

    for attempt in range(max_retries):
        try:
            async with nacos_registry:
                local_ip = get_local_ip()

                # 构建元数据
                metadata = {
                    "version": "1.0.0",
                    "framework": framework,
                    "environment": os.getenv("ENVIRONMENT", "development"),
                    "description": description
                }
                if additional_metadata:
                    metadata.update(additional_metadata)

                service_config = {
                    "serviceName": service_name,
                    "ip": local_ip,
                    "port": service_port,
                    "groupName": "DEFAULT_GROUP",
                    "clusterName": "DEFAULT",
                    "namespaceId": "",
                    "weight": 1.0,
                    "enabled": True,
                    "healthy": True,
                    "ephemeral": True,
                    "metadata": metadata
                }

                success = await nacos_registry.register_service(service_config)
                if success:
                    logger.info(f"✅ 服务已注册到 Nacos: {local_ip}:{service_port}")

                    # 启动心跳任务
                    if heartbeat_task is None:
                        heartbeat_task = asyncio.create_task(
                            heartbeat_task_func(heartbeat_interval)
                        )
                        logger.info("💓 心跳任务已启动")

                    return True
                else:
                    logger.warning(f"⚠️ 服务注册失败 (尝试 {attempt + 1}/{max_retries})")

        except Exception as e:
            logger.error(f"❌ Nacos注册过程中出错 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"等待 {retry_delay} 秒后重试...")
                await asyncio.sleep(retry_delay)

    logger.error("❌ 服务注册最终失败，但服务继续运行")
    return False


async def initialize_nacos(nacos_url: Optional[str] = None) -> bool:
    """
    初始化 Nacos 注册器

    Args:
        nacos_url: Nacos 服务地址，默认从环境变量获取

    Returns:
        bool: 初始化是否成功
    """
    global nacos_registry

    if nacos_url is None:
        nacos_url = os.getenv("NACOS_SERVER_URL", "http://localhost:8848")

    nacos_registry = NacosRegistry(nacos_url)
    logger.info(f"🔧 Nacos 注册器已初始化: {nacos_url}")
    return True


async def cleanup_nacos():
    """清理 Nacos 相关资源"""
    global heartbeat_task

    logger.info("🛑 正在清理 Nacos 资源...")

    # 停止心跳任务
    if heartbeat_task:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        logger.info("💓 心跳任务已停止")

    # 关闭注册器
    global nacos_registry
    if nacos_registry:
        # Context manager 会自动清理 session
        nacos_registry = None
        logger.info("🔧 Nacos 注册器已清理")


# 使用示例
if __name__ == "__main__":
    async def example_usage():
        """使用示例"""
        # 1. 初始化
        await initialize_nacos()

        # 2. 注册服务
        success = await register_to_nacos(
            service_name="example-service",
            service_port=8080,
            framework="FastAPI",
            description="示例服务",
            additional_metadata={
                "team": "backend",
                "repository": "https://github.com/example/service"
            }
        )

        if success:
            print("✅ 服务注册成功")

        # 3. 模拟服务运行
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            print("🛑 服务正在关闭...")

        # 4. 清理资源
        await cleanup_nacos()

    # 运行示例
    asyncio.run(example_usage())