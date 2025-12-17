# -*- coding: utf-8 -*-
"""
DataSourceGateway 集成示例

展示如何在 get-stockdata 服务中使用 DataSourceGateway
"""

import asyncio
import logging
from datasource.v1 import data_source_pb2

from src.gateway import DataSourceGateway

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """演示 DataSourceGateway 使用"""
    
    # 1. 初始化网关
    logger.info("=== Initializing DataSourceGateway ===")
    gateway = DataSourceGateway(enable_circuit_breaker=True)
    await gateway.initialize()
    
    logger.info("Gateway initialized successfully!")
    logger.info(f"Available chains: {list(gateway._chains.keys())}")
    
    # 2. 获取行情数据
    logger.info("\n=== Fetching QUOTES data ===")
    quotes_request = data_source_pb2.DataRequest(
        type=data_source_pb2.DATA_TYPE_QUOTES,
        codes=["000001", "600519"],
        request_id="demo-001"
    )
    
    quotes_response = await gateway.fetch(quotes_request)
    logger.info(f"Quotes Response:")
    logger.info(f"  Success: {quotes_response.success}")
    logger.info(f"  Source: {quotes_response.source_name}")
    logger.info(f"  Latency: {quotes_response.latency_ms}ms")
    if not quotes_response.success:
        logger.error(f"  Error: {quotes_response.error_message}")
    
    # 3. 获取历史数据（测试降级）
    logger.info("\n=== Fetching HISTORY data (fallback test) ===")
    history_request = data_source_pb2.DataRequest(
        type=data_source_pb2.DATA_TYPE_HISTORY,
        codes=["000001"],
        params={
            "frequency": "d",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        },
        request_id="demo-002"
    )
    
    history_response = await gateway.fetch(history_request)
    logger.info(f"History Response:")
    logger.info(f"  Success: {history_response.success}")
    logger.info(f"  Source: {history_response.source_name}")
    logger.info(f"  Latency: {history_response.latency_ms}ms")
    if not history_response.success:
        logger.error(f"  Error: {history_response.error_message}")
    
    # 4. 获取榜单数据
    logger.info("\n=== Fetching RANKING data ===")
    ranking_request = data_source_pb2.DataRequest(
        type=data_source_pb2.DATA_TYPE_RANKING,
        params={"type": "hot"},
        request_id="demo-003"
    )
    
    ranking_response = await gateway.fetch(ranking_request)
    logger.info(f"Ranking Response:")
    logger.info(f"  Success: {ranking_response.success}")
    logger.info(f"  Source: {ranking_response.source_name}")
    logger.info(f"  Latency: {ranking_response.latency_ms}ms")
    if not ranking_response.success:
        logger.error(f"  Error: {ranking_response.error_message}")
    
    # 5. 查看统计信息
    logger.info("\n=== Gateway Statistics ===")
    stats = gateway.get_stats()
    for data_type, chain_stats in stats.items():
        logger.info(f"\nData Type: {data_type}")
        logger.info(f"  Total Requests: {chain_stats['total_requests']}")
        logger.info(f"  Primary Success: {chain_stats['primary_success']}")
        logger.info(f"  Fallback Success: {chain_stats['fallback_success']}")
        logger.info(f"  All Failed: {chain_stats['all_failed']}")
        logger.info(f"  Overall Success Rate: {chain_stats['overall_success_rate']}")
        
        logger.info(f"  Providers:")
        for provider_name, provider_stats in chain_stats.get('providers', {}).items():
            logger.info(f"    - {provider_name}:")
            logger.info(f"        Success Rate: {provider_stats['success_rate']}")
            logger.info(f"        Avg Latency: {provider_stats['avg_latency_ms']}ms")
            if provider_stats['last_error']:
                logger.info(f"        Last Error: {provider_stats['last_error']}")
    
    # 6. 关闭网关
    logger.info("\n=== Closing Gateway ===")
    await gateway.close()
    logger.info("Gateway closed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
