"""
流动性数据访问对象 (Tencent Cloud MySQL)
"""
import logging
from typing import Dict, Any, List
from datetime import date
from data_access.mysql_pool import MySQLPoolManager

logger = logging.getLogger(__name__)

class LiquidityDAO:
    """处理 market_review_liquidity 表的持久化逻辑"""

    def __init__(self):
        self.table_name = "market_review_liquidity"

    async def upsert_liquidity_record(self, data: Dict[str, Any]):
        """
        更新或插入流动性记录 (基于 trade_date)
        
        Args:
            data: 包含 trade_date, vol_ma_divergence 等字段的字典
        """
        pool = await MySQLPoolManager.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 提取字段
                trade_date = data.get("trade_date")
                if isinstance(trade_date, str):
                    trade_date = trade_date.replace('-', '')
                
                # 构建 Upsert 语句
                sql = f"""
                INSERT INTO {self.table_name}
                (trade_date, vol_ma_divergence, vol_rank, vol_ma5_rank, vol_ma20_rank, vol_01_state, 
                 margin_ratio, margin_velocity, vol_02_state, 
                 congestion_velocity, zombie_stock_derivation, 
                 cost_pulse_fdr007, non_bank_premium, etf_depletion_rate, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON DUPLICATE KEY UPDATE
                vol_ma_divergence = VALUES(vol_ma_divergence),
                vol_rank = VALUES(vol_rank),
                vol_ma5_rank = VALUES(vol_ma5_rank),
                vol_ma20_rank = VALUES(vol_ma20_rank),
                vol_01_state = VALUES(vol_01_state),
                margin_ratio = VALUES(margin_ratio),
                margin_velocity = VALUES(margin_velocity),
                vol_02_state = VALUES(vol_02_state),
                congestion_velocity = VALUES(congestion_velocity),
                zombie_stock_derivation = VALUES(zombie_stock_derivation),
                cost_pulse_fdr007 = VALUES(cost_pulse_fdr007),
                non_bank_premium = VALUES(non_bank_premium),
                etf_depletion_rate = VALUES(etf_depletion_rate),
                updated_at = CURRENT_TIMESTAMP
                """
                
                params = (
                    trade_date,
                    data.get("vol_ma_divergence"),
                    data.get("vol_rank"),
                    data.get("vol_ma5_rank"),
                    data.get("vol_ma20_rank"),
                    data.get("state_name", "NORMAL"),
                    data.get("margin_ratio"),
                    data.get("margin_velocity"),
                    data.get("vol_02_state", "NORMAL"),
                    data.get("congestion_velocity"),
                    data.get("zombie_stock_derivation"),
                    data.get("cost_pulse_fdr007"),
                    data.get("non_bank_premium"),
                    data.get("etf_depletion_rate")
                )
                
                try:
                    await cursor.execute(sql, params)
                    await conn.commit()
                    logger.info(f"✓ MySQL Upsert Successful: {trade_date} (vol05={data.get('cost_pulse_fdr007')}, vol06={data.get('etf_depletion_rate')})")
                except Exception as e:
                    logger.error(f"Failed to upsert liquidity data: {e}")
                    raise
