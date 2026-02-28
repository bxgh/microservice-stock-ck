import asyncio
import logging
from typing import List

from dao.altdata import AltDataDAO
from strategies.alt_data.eco_signal_strategy import EcoSignalStrategy

logger = logging.getLogger(__name__)


async def run_eco_signal_generation(labels: List[str] = None):
    """
    每日定时跑批任务：
    针对指定的一组技术生态标签，从数据湖获取过去 45 天原始行为特征。
    送入 EcoSignalStrategy 计算复合动量与 Z-Score，落盘至 ecosystem_signals 表。
    """
    if labels is None:
        # 默认列表，日后可由配置加载
        labels = ["deepseek", "vllm", "paddle", "mindspore", "sglang"]
        
    logger.info(f"Starting ecosystem signal generation for labels: {labels}")
    
    dao = AltDataDAO()
    strategy = EcoSignalStrategy()
    
    success_count = 0
    
    for label in labels:
        try:
            # 1. 提取至少能够撑起 30 天滑动窗口的数据
            raw_df = dao.get_raw_metrics(label=label, lookback_days=45)
            
            if raw_df is None or raw_df.empty:
                logger.warning(f"No raw data found for label: {label}. Skipping.")
                continue
                
            # 2. 从原始行为特征生成标准 Z 评分信号
            signal_df = strategy.generate_signals(raw_df)
            
            if signal_df is not None and not signal_df.empty:
                # 3. 将计算好的具有分级的信号写入表
                dao.insert_signals(signal_df)
                success_count += 1
                logger.info(f"Successfully generated and stored signals for {label}")
            else:
                logger.warning(f"Strategy returned empty signal for {label}")
                
        except Exception as e:
            logger.error(f"Failed processing eco signals for {label}: {e}", exc_info=True)
            
    logger.info(f"Finished eco signal generation. Success: {success_count}/{len(labels)}")

if __name__ == '__main__':
    asyncio.run(run_eco_signal_generation())
