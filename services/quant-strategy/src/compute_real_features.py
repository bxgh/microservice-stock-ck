import asyncio
import logging
import pandas as pd
from datetime import datetime
from src.core.factory import StrategyFactory
from src.orchestrator.peer_selector import PeerSelector

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("compute-real-features")

async def main():
    target_code = "688802.SH"
    trade_date = "2026-02-05"
    
    factory = StrategyFactory()
    peer_selector = PeerSelector()
    
    try:
        # 1. 初始化引擎
        await factory.initialize()
        
        # 2. 获取该行业下有数据的对标股
        logger.info(f"🔍 正在获取 {target_code} 在 {trade_date} 的对标股...")
        selection = await peer_selector.select_peers(target_code)
        
        # 强制加上 688802.sh (因为 factory.compute_and_store 会处理代码标准化)
        all_codes = list(set([target_code] + selection.peers))
        
        logger.info(f"🚀 开始为 {len(all_codes)} 只个股计算真实特征 (日期: {trade_date})...")
        
        success_count = 0
        failed_codes = []
        
        for code in all_codes:
            logger.info(f"计算中: {code}...")
            success = await factory.compute_and_store(code, trade_date, skip_gate_check=True)
            if success:
                success_count += 1
            else:
                failed_codes.append(code)
        
        logger.info(f"✅ 完成! 成功: {success_count}, 失败: {len(failed_codes)}")
        if failed_codes:
            logger.warning(f"失败列表: {failed_codes}")
            
    except Exception as e:
        logger.error(f"❌ 运行出错: {e}", exc_info=True)
    finally:
        await factory.close()

if __name__ == "__main__":
    asyncio.run(main())
