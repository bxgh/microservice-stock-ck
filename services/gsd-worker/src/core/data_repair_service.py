"""
数据修复服务 (Data Repair Service)

功能:
1. 从 stock_health_ledger 捞取异常股票
2. 通过 gRPC 从 mootdx-source 补采缺失数据
3. 写入 MySQL stock_kline_daily
4. 同步数据到 ClickHouse
5. 更新修复状态
"""

import asyncio
import logging
import json
import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

from data_access.mysql_pool import MySQLPoolManager
from core.sync_service import KLineSyncService
from grpc_client.client import DataSourceClient  # 我们需要复制这个客户端到 worker

logger = logging.getLogger(__name__)

class DataRepairService:
    """数据修复服务"""
    
    def __init__(self):
        self.sync_service = KLineSyncService()
        self.ds_client = None
        self.mysql_pool = None
        
    async def initialize(self) -> None:
        """初始化"""
        await self.sync_service.initialize()
        
        # 初始化 gRPC 客户端
        server_url = os.getenv("MOOTDX_SOURCE_URL", "127.0.0.1:50051")
        self.ds_client = DataSourceClient(server_url=server_url)
        await self.ds_client.initialize()
        
        self.mysql_pool = await MySQLPoolManager.get_pool()
        logger.info("✓ DataRepairService 初始化完成")
        
    async def close(self) -> None:
        """关闭"""
        try:
            await self.sync_service.close()
        finally:
            if self.ds_client:
                await self.ds_client.close()
            
    async def get_repair_candidates(self, limit: int = 10) -> List[Dict[str, Any]]:
        """从 ledger 中获取待修复股票"""
        import aiomysql
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT stock_code, missing_count, missing_details 
                    FROM stock_health_ledger 
                    WHERE status = 'ERROR' AND repair_status = 0
                    ORDER BY missing_count ASC
                    LIMIT %s
                """
                await cursor.execute(sql, (limit,))
                return await cursor.fetchall()

    async def _insert_to_mysql(self, df: pd.DataFrame) -> None:
        """将补采数据写入 MySQL"""
        if df.empty:
            return
            
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    # 转换字段名以匹配 MySQL 表结构
                    sql = """
                    INSERT INTO stock_kline_daily 
                    (code, trade_date, open, high, low, close, volume, amount, turnover, pct_chg)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        open=VALUES(open), high=VALUES(high), low=VALUES(low), 
                        close=VALUES(close), volume=VALUES(volume), amount=VALUES(amount)
                    """
                    
                    records = []
                    for _, row in df.iterrows():
                        records.append((
                            row.get('code'),
                            row.get('date'),
                            row.get('open'),
                            row.get('high'),
                            row.get('low'),
                            row.get('close'),
                            row.get('volume'),
                            row.get('amount'),
                            row.get('turnover'),
                            row.get('pct_chg')
                        ))
                    
                    await cursor.executemany(sql, records)
                    await conn.commit()
                except Exception as e:
                    await conn.rollback()
                    raise
                
    async def _update_repair_status(self, stock_code: str, status: int = 1) -> None:
        """更新修复状态"""
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    sql = "UPDATE stock_health_ledger SET repair_status = %s WHERE stock_code = %s"
                    await cursor.execute(sql, (status, stock_code))
                    await conn.commit()
                except Exception as e:
                    await conn.rollback()
                    raise

    async def repair_stock(self, stock_code: str, missing_dates: List[str]) -> bool:
        """修复单只股票"""
        logger.info(f"正在修复股票 {stock_code}, 缺失日期数: {len(missing_dates)}")
        
        # 为了效率，我们按范围补采
        if not missing_dates:
            logger.warning(f"股票 {stock_code} 缺失日期列表为空")
            return False
            
        start_date = min(missing_dates)
        end_date = max(missing_dates)
        
        try:
            # 1. 从 gRPC 获取数据
            df = await self.ds_client.fetch_history(
                code=stock_code,
                start_date=start_date,
                end_date=end_date,
                adjust="2"  # 后复权
            )
            
            if df.empty:
                logger.warning(f"补采 {stock_code} 返回空数据")
                return False
                
            # 2. 写入 MySQL
            await self._insert_to_mysql(df)
            logger.info(f"✓ {stock_code} 补采数据已写入 MySQL")
            
            # 3. 触发 ClickHouse 同步
            await self.sync_service.sync_by_stock_codes([stock_code])
            logger.info(f"✓ {stock_code} 已同步到 ClickHouse")
            
            # 4. 更新状态
            await self._update_repair_status(stock_code, 1)
            return True
            
        except Exception as e:
            logger.error(f"修复股票 {stock_code} 失败: {e}", exc_info=True)
            return False

    async def run_repair_batch(self, limit: int = 10) -> None:
        """运行批量修复"""
        candidates = await self.get_repair_candidates(limit=limit)
        if not candidates:
            logger.info("没有待修复的异常股票")
            return
            
        logger.info(f"开启批量修复任务, 待修复数: {len(candidates)}")
        
        success_count = 0
        for item in candidates:
            code = item['stock_code']
            dates = json.loads(item['missing_details']) if isinstance(item['missing_details'], str) else item['missing_details']
            
            if await self.repair_stock(code, dates):
                success_count += 1
                
        logger.info(f"批量修复完成: 成功 {success_count}/{len(candidates)}")
