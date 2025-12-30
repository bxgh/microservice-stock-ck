"""
Mootdx Snapshot POC (Proof of Concept)
测试批量获取股票行情快照的速度（内网环境下应达到秒级）
"""
import asyncio
import sys
import os
import time
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src')

from collectors.datasource import DataSourceCollector
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_snapshot_speed():
    collector = DataSourceCollector()
    await collector.initialize()
    
    try:
        # 1. 获取部分股票列表 (前 240 只，即 3 个 batch)
        logger.info("获取测试股票列表...")
        all_stocks = await collector.get_stock_list()
        test_codes = all_stocks[:240]
        
        if not test_codes:
            logger.error("未能获取股票列表")
            return

        batch_size = 80 # Mootdx TCP 每批次上限通常为 80
        logger.info(f"测试股票数量: {len(test_codes)}, 批次大小: {batch_size}")
        
        start_time = time.time()
        
        # 2. 分批请求快照
        results = []
        for i in range(0, len(test_codes), batch_size):
            batch = test_codes[i:i+batch_size]
            logger.info(f"正在请求第 {i//batch_size + 1} 批...")
            
            # 使用 DataSourceCollector 直接调用 gRPC 接口
            df = await collector.client.fetch_quotes(
                codes=batch,
                params={}
            )
            
            if not df.empty:
                results.extend(df.to_dict('records'))
                logger.info(f"  ✅ 批次完成，收到 {len(df)} 条快照")

        end_time = time.time()
        total_time = end_time - start_time
        
        # 3. 性能分析
        logger.info("="*50)
        logger.info(f"🚀 性能统计:")
        logger.info(f"  总耗时: {total_time:.2f} 秒")
        logger.info(f"  平均每批耗时: {total_time / (len(test_codes)/batch_size):.4f} 秒")
        logger.info(f"  预估全市场 (5400支) 耗时: {(total_time / len(test_codes) * 5400):.2f} 秒")
        logger.info("="*50)
        
        if results:
            logger.info(f"数据样本 (第一条): {results[0]}")

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
    finally:
        await collector.close()

if __name__ == "__main__":
    asyncio.run(test_snapshot_speed())
