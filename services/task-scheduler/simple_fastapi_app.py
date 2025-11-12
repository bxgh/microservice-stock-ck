#!/usr/bin/env python3
"""
FastAPI Task Scheduler - 最小化演示版本
包含Nacos服务注册和基本API功能
"""

import asyncio
import logging
import sys
import os
import json
import socket
from datetime import datetime
from contextlib import asynccontextmanager

import aiohttp
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# 全局变量
nacos_registry = None
heartbeat_task = None
service_config = None

class SimpleNacosRegistry:
    """简化的Nacos服务注册类"""

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
                        logger.info(f"💓 心跳发送成功: {service_config.get('serviceName')}")
                        return True
                logger.warning(f"⚠️ 心跳发送失败: {response.status} - {await response.text()}")
                return False
        except Exception as e:
            logger.error(f"❌ 心跳发送异常: {e}")
            return False

def get_local_ip():
    """获取本地IP地址"""
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    await startup()
    yield
    # 关闭时清理
    await shutdown()

async def startup():
    """启动初始化"""
    global nacos_registry

    logger.info("🚀 启动 FastAPI Task Scheduler...")

    # 初始化Nacos注册器
    nacos_url = os.getenv("NACOS_SERVER_URL", "http://localhost:8848")
    nacos_registry = SimpleNacosRegistry(nacos_url)

    # 注册服务到Nacos
    await register_to_nacos()

    logger.info("✅ FastAPI Task Scheduler 启动成功!")

async def heartbeat_task_func():
    """心跳任务"""
    global nacos_registry, service_config

    heartbeat_interval = 10  # 每10秒发送一次心跳

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

async def register_to_nacos():
    """注册服务到Nacos"""
    global nacos_registry, service_config

    max_retries = 3
    retry_delay = 5  # 秒

    for attempt in range(max_retries):
        try:
            async with nacos_registry:
                local_ip = get_local_ip()
                port = int(os.getenv("SERVICE_PORT", "8081"))

                service_config = {
                    "serviceName": "task-scheduler",
                    "ip": local_ip,
                    "port": port,
                    "groupName": "DEFAULT_GROUP",
                    "clusterName": "DEFAULT",
                    "namespaceId": "",
                    "weight": 1.0,
                    "enabled": True,
                    "healthy": True,
                    "ephemeral": True,
                    "metadata": {
                        "version": "1.0.0",
                        "framework": "FastAPI",
                        "environment": os.getenv("ENVIRONMENT", "development"),
                        "description": "TaskScheduler 微服务 - FastAPI架构版本"
                    }
                }

                success = await nacos_registry.register_service(service_config)
                if success:
                    logger.info(f"✅ 服务已注册到 Nacos: {local_ip}:{port}")

                    # 启动心跳任务
                    global heartbeat_task
                    if heartbeat_task is None:
                        heartbeat_task = asyncio.create_task(heartbeat_task_func())
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

async def shutdown():
    """关闭清理"""
    global heartbeat_task

    logger.info("🛑 FastAPI Task Scheduler 正在关闭...")

    # 停止心跳任务
    if heartbeat_task:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
        logger.info("💓 心跳任务已停止")

def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="Task Scheduler API",
        description="TaskScheduler 微服务 - FastAPI架构版本",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 根路径
    @app.get("/", tags=["root"])
    async def root():
        """根路径"""
        return {
            "service": "Task Scheduler",
            "framework": "FastAPI",
            "version": "1.0.0",
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "docs": "/docs",
            "health": "/health",
            "nacos_status": "registered" if nacos_registry else "not_registered"
        }

    # 健康检查
    @app.get("/health", tags=["health"])
    async def health():
        """健康检查"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "task-scheduler",
            "framework": "FastAPI",
            "nacos_registered": nacos_registry is not None
        }

    # 服务信息
    @app.get("/info", tags=["info"])
    async def info():
        """服务信息"""
        return {
            "service_name": "task-scheduler",
            "framework": "FastAPI + uvicorn",
            "version": "1.0.0",
            "architecture": "layered",
            "features": [
                "Nacos服务注册发现",
                "健康检查",
                "RESTful API",
                "CORS支持",
                "自动文档生成"
            ],
            "environment": os.getenv("ENVIRONMENT", "development"),
            "local_ip": get_local_ip(),
            "port": os.getenv("SERVICE_PORT", "8081"),
            "nacos_url": os.getenv("NACOS_SERVER_URL", "http://localhost:8848")
        }

    # 任务列表占位符
    @app.get("/tasks", tags=["tasks"])
    async def list_tasks():
        """获取任务列表"""
        return {
            "tasks": [],
            "total": 0,
            "message": "Task Scheduler 已准备就绪",
            "framework": "FastAPI",
            "scheduler_status": "ready"
        }

    # 统计信息
    @app.get("/stats", tags=["stats"])
    async def stats():
        """获取统计信息"""
        return {
            "service": "task-scheduler",
            "uptime": "running",
            "tasks": {
                "total": 0,
                "running": 0,
                "completed": 0,
                "failed": 0
            },
            "system": {
                "framework": "FastAPI",
                "nacos_status": "connected" if nacos_registry else "disconnected",
                "memory_usage": "normal",
                "cpu_usage": "normal"
            }
        }

    # 异常处理器
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"未处理异常: {exc}", exc_info=True)
        return {
            "error": "Internal Server Error",
            "detail": str(exc),
            "path": str(request.url.path)
        }

    return app

# 创建应用实例
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("SERVICE_PORT", "8081"))
    host = os.getenv("SERVICE_HOST", "0.0.0.0")

    logger.info(f"🌐 启动服务: http://{host}:{port}")
    logger.info(f"📚 API文档: http://{host}:{port}/docs")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )