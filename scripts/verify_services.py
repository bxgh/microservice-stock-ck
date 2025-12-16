import sys
import os
import asyncio
import grpc
import logging

# Add generated code path
sys.path.append(os.path.join(os.path.dirname(__file__), '../libs/common'))

from datasource.v1 import data_source_pb2
from datasource.v1 import data_source_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify")

async def test_service(name, port):
    target = f"localhost:{port}"
    logger.info(f"Connecting to {name} at {target}...")
    
    async with grpc.aio.insecure_channel(target) as channel:
        stub = data_source_pb2_grpc.DataSourceServiceStub(channel)
        
        # 1. HealthCheck
        try:
            health = await stub.HealthCheck(data_source_pb2.Empty())
            logger.info(f"[{name}] Health: {health.healthy}, Message: {health.message}")
        except grpc.RpcError as e:
            logger.error(f"[{name}] HealthCheck failed: {e}")
            return

        # 2. GetCapabilities
        try:
            caps = await stub.GetCapabilities(data_source_pb2.Empty())
            logger.info(f"[{name}] Capabilities: {caps.supported_types}, Version: {caps.version}")
        except grpc.RpcError as e:
            logger.error(f"[{name}] GetCapabilities failed: {e}")
            
        # 3. FetchData (Simple Test)
        try:
            # Mootdx Quote
            if name == "mootdx":
                req = data_source_pb2.DataRequest(
                    type=data_source_pb2.DATA_TYPE_QUOTES,
                    codes=["600519"]
                )
                resp = await stub.FetchData(req)
                logger.info(f"[{name}] FetchData: Success={resp.success}, Source={resp.source_name}, Latency={resp.latency_ms}ms")
                # logger.info(f"Data: {resp.json_data[:100]}...")

            # AkShare Ranking
            elif name == "akshare":
                req = data_source_pb2.DataRequest(
                    type=data_source_pb2.DATA_TYPE_RANKING,
                    params={"date": "20231215"} 
                )
                # Note: AkShare remote call might fail if endpoint is wrong, but let's test connectivity
                resp = await stub.FetchData(req)
                logger.info(f"[{name}] FetchData: Success={resp.success}, Source={resp.source_name}, Latency={resp.latency_ms}ms")
                if not resp.success:
                    logger.error(f"Error: {resp.error_message}")

        except grpc.RpcError as e:
            logger.error(f"[{name}] FetchData failed: {e}")

async def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    logger.info(f"Target host: {host}")
    
    await asyncio.gather(
        test_service("mootdx", 50051), # Port map: 50051 -> host:50051
        test_service("akshare", 50052) # Port map: 50052 -> host:50052
    )

if __name__ == "__main__":
    asyncio.run(main())
