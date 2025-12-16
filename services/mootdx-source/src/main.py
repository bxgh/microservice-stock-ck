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
        self.nacos_client = None
        self.service_name = os.getenv("SERVICE_NAME", "mootdx-source")
        self.service_host = os.getenv("SERVICE_HOST", "127.0.0.1")
        self.service_port = int(os.getenv("SERVICE_PORT", "50051"))
        self.nacos_addr = os.getenv("NACOS_SERVER_ADDR", "127.0.0.1:8848")

    def register_nacos(self):
        """注册服务到 Nacos"""
        try:
            logger.info(f"Registering to Nacos: {self.nacos_addr}...")
            self.nacos_client = nacos.NacosClient(self.nacos_addr, namespace="")
            self.nacos_client.add_naming_instance(
                self.service_name,
                self.service_host,
                self.service_port,
                cluster_name="DEFAULT",
                metadata={"version": "1.0.0", "type": "grpc", "capabilities": "QUOTES,TICK,HISTORY"}
            )
            logger.info(f"Registered {self.service_name} at {self.service_host}:{self.service_port}")
        except Exception as e:
            logger.error(f"Failed to register to Nacos: {e}")
            # 不阻断启动，可能是 Nacos 暂时不可用，后续已有重试或忽略策略

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
        self.server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
        data_source_pb2_grpc.add_DataSourceServiceServicer_to_server(
            MooTDXService(), self.server
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
            pass
        finally:
            self.deregister_nacos()

    async def shutdown(self):
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
