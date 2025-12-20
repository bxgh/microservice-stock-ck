import asyncio
import logging
import os
import signal
import sys
from concurrent import futures

import grpc
import nacos

# 添加 libs/common 到路径 (虽然 Dockerfile 做了，但为了 IDE 或本地运行)
sys.path.append(os.path.join(os.path.dirname(__file__), '../../libs/common'))

from datasource.v1 import data_source_pb2_grpc
from service import MooTDXService

# 配置日志
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mootdx-source")

class Server:
    def __init__(self):
        self.server = None
        self.service = None  # Track service instance
        self.nacos_client = None
        self.service_name = os.getenv("SERVICE_NAME", "mootdx-source")
        self.service_host = os.getenv("SERVICE_HOST", "127.0.0.1")
        self.service_port = int(os.getenv("SERVICE_PORT", "50051"))
        self.nacos_addr = os.getenv("NACOS_SERVER_ADDR", "127.0.0.1:8848")
        self.max_workers = int(os.getenv("GRPC_MAX_WORKERS", "10"))

    def register_nacos(self):
        """注册服务到 Nacos"""
        try:
            logger.info(f"Registering to Nacos: {self.nacos_addr}...")
            self.nacos_client = nacos.NacosClient(self.nacos_addr, namespace="")
            
            # 从 service 动态获取 capabilities
            capabilities = "ALL" if self.service else "UNKNOWN"
            
            self.nacos_client.add_naming_instance(
                self.service_name,
                self.service_host,
                self.service_port,
                cluster_name="DEFAULT",
                metadata={
                    "version": "2.0.0-hybrid", 
                    "type": "grpc", 
                    "capabilities": capabilities
                }
            )
            logger.info(f"Registered {self.service_name} at {self.service_host}:{self.service_port}")
        except Exception as e:
            logger.error(f"Failed to register to Nacos: {e}")
            # 不阻断启动，可能是 Nacos 暂时不可用

    def deregister_nacos(self):
        """注销服务"""
        if self.nacos_client:
            try:
                self.nacos_client.remove_naming_instance(
                    self.service_name,
                    self.service_host,
                    self.service_port
                )
                logger.info("Deregistered from Nacos")
            except Exception as e:
                logger.error(f"Failed to deregister: {e}")

    async def serve(self):
        """启动 gRPC 服务"""
        try:
            # 创建 gRPC 服务器
            self.server = grpc.aio.server(
                futures.ThreadPoolExecutor(max_workers=self.max_workers)
            )
            
            # 创建并初始化服务实例
            self.service = MooTDXService()
            try:
                await self.service.initialize()
            except Exception as e:
                logger.error(f"Service initialization failed: {e}")
                await self._cleanup_service()
                raise
            
            # 注册服务
            data_source_pb2_grpc.add_DataSourceServiceServicer_to_server(
                self.service, self.server
            )
            
            listen_addr = f"[::]:{self.service_port}"
            self.server.add_insecure_port(listen_addr)
            
            logger.info(f"Starting gRPC server on {listen_addr}")
            await self.server.start()
            
            # 注册 Nacos
            self.register_nacos()
            
            # 等待终止信号
            try:
                await self.server.wait_for_termination()
            except asyncio.CancelledError:
                logger.info("Server cancelled")
            finally:
                await self._cleanup()
        
        except Exception as e:
            logger.error(f"Server startup failed: {e}", exc_info=True)
            await self._cleanup()
            raise

    async def _cleanup_service(self):
        """清理服务实例"""
        if self.service:
            try:
                await self.service.close()
            except Exception as e:
                logger.error(f"Error closing service: {e}")
            finally:
                self.service = None

    async def _cleanup(self):
        """清理所有资源"""
        await self._cleanup_service()
        self.deregister_nacos()

    async def shutdown(self):
        """优雅关闭服务器"""
        logger.info("Stopping server...")
        if self.server:
            await self.server.stop(5)

async def main():
    server = Server()
    
    # 信号处理
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(server.shutdown()))
        
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
