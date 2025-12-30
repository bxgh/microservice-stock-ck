"""
Mootdx XDXR POC
测试获取股票除权除息数据（用于计算复权因子）
"""
import asyncio
import sys
import os
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src')

from collectors.datasource import DataSourceCollector
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_factor_data():
    collector = DataSourceCollector()
    await collector.initialize()
    
    try:
        test_code = "600519" # 贵州茅台
        logger.info(f"正在获取 {test_code} 的除权除息数据 (XDXR)...")
        
        # 使用 DataSourceClient 的 fetch_data 模拟获取 XDXR
        # 在实际实现中，我们将添加专门的 fetch_xdxr 接口
        # 为了 POC，我们通过 params 传参。假设 DataType=10 (META/XDXR)
        
        # 暂时手动调用 client 的 internal 方法
        df = await collector.client.fetch_meta(test_code)
        
        logger.info(f"获取到元数据/XD数据样例:")
        if not df.empty:
            print(df.head())
        else:
            logger.warning("未获取到数据，可能是接口未实现完全")

        # 验证 Baostock 接口能力
        logger.info("验证 Baostock 历史复权因子接口...")
        # hist 接口本身支持获取 factor
        df_hist = await collector.client.fetch_history(
            test_code, 
            start_date="2023-01-01", 
            end_date="2023-12-31",
            adjust="3" # 不复权，观察是否有 factor 字段
        )
        
        if not df_hist.empty:
            logger.info(f"历史数据列名: {df_hist.columns.tolist()}")
            if 'fore_factor' in df_hist.columns:
                logger.info("✅ 接口已支持返回复权因子")
        
    finally:
        await collector.close()

if __name__ == "__main__":
    asyncio.run(test_factor_data())
