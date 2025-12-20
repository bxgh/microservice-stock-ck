import asyncio
import logging
import os
import signal
import sys
import grpc
import nacos
from concurrent import futures

# Add project root to python path to import common libs
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datasource.v1 import data_source_pb2_grpc
from service import BaostockService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("baostock-source")


class BaostockMicroservice:
    def __init__(self):
        # Defers server creation to start() to ensure correct event loop
        self.server = None
        self.service = BaostockService()
        
        # Config
        self.service_name = os.getenv("SERVICE_NAME", "baostock-source")
        self.host = os.getenv("SERVICE_HOST", "127.0.0.1")
        self.port = int(os.getenv("SERVICE_PORT", "50054"))
        self.nacos_addr = os.getenv("NACOS_SERVER_ADDR", "127.0.0.1:8848")
        
    async def start(self):
        # Create server in the current running loop
        self.server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
        data_source_pb2_grpc.add_DataSourceServiceServicer_to_server(
            self.service, self.server
        )
        
        # Start gRPC server
        address = f"[::]:{self.port}"
        self.server.add_insecure_port(address)
        logger.info(f"Starting gRPC server on {address}")
        await self.server.start()
        
        # Register to Nacos
        await self._register_nacos()
        
        # Wait for termination
        shutdown_event = asyncio.Event()
        
        def signal_handler(*args):
            logger.info("Received shutdown signal")
            shutdown_event.set()
            
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, signal_handler)
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        
        await shutdown_event.wait()
        
        # Graceful shutdown
        logger.info("Stopping gRPC server...")
        await self.server.stop(5)
        
    async def _register_nacos(self):
        try:
            logger.info(f"Registering to Nacos: {self.nacos_addr}")
            client = nacos.NacosClient(self.nacos_addr, namespace="public")
            client.add_naming_instance(
                self.service_name,
                self.host,
                self.port,
                cluster_name="DEFAULT",
                metadata={"version": "1.0"}
            )
            logger.info(f"Registered {self.service_name} at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Nacos registration failed: {e}")

async def main():
    ms = BaostockMicroservice()
    await ms.start()

if __name__ == "__main__":
    asyncio.run(main())
