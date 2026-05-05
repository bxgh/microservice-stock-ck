"""
Weekly Data Consistency Audit Service
"""
import asyncio
import aiomysql
import asynch
import os
import logging
from datetime import datetime
from collections import namedtuple
from typing import Dict, Tuple, List

from core.sync_service import KLineSyncService
from core.exceptions import DataMismatchException

logger = logging.getLogger(__name__)

# Fingerprint: (count, sum_volume)
Fingerprint = namedtuple('Fingerprint', ['count', 'volume_sum'])

class WeeklyAuditService:
    """
    每周深度审计服务
    
    采用“全量聚合指纹” (Full Aggregation Fingerprinting) 策略，
    对比 MySQL 和 ClickHouse 的全量数据一致性。
    """
    
    def __init__(self):
        self.mysql_pool = None
        self.clickhouse_pool = None
        self.sync_service = KLineSyncService() # Reuse sync service for healing
        
        # Configuration Constants
        self.BATCH_SIZE = 100
        self.VOLUME_TOLERANCE = 0.1  # Allow 0.1 difference for floating point comparison
    
    async def initialize(self):
        """Initialize resources"""
        # Reuse pools from sync_service to ensure consistent config
        await self.sync_service.initialize()
        self.mysql_pool = self.sync_service.mysql_pool
        self.clickhouse_pool = self.sync_service.clickhouse_pool
        
    async def close(self):
        await self.sync_service.close()

    async def run_full_audit(self):
        """
        执行全量审计的主入口
        """
        start_time = datetime.now()
        logger.info("🛡️ 开始每周全量数据审计 (Weekly Deep Audit)...")
        
        try:
            # 1. 获取指纹
            mysql_fp = await self._get_mysql_fingerprints()
            ch_fp = await self._get_clickhouse_fingerprints()
            
            # 2. 对比并识别脏数据
            mismatched_codes, missing_in_ch, missing_in_mysql = self._compare_fingerprints(mysql_fp, ch_fp)
            
            total_issues = len(mismatched_codes) + len(missing_in_ch) + len(missing_in_mysql)
            
            if total_issues == 0:
                msg = f"✅ 审计通过！MySQL({len(mysql_fp)}) 与 ClickHouse({len(ch_fp)}) 数据完全一致。"
                logger.info(msg)
                await self.sync_service._log_to_db("SUCCESS", 0, msg, (datetime.now() - start_time).total_seconds(), task_name="weekly_deep_audit")
                return
            
            # 3. 自动修复 (Self-Healing)
            logger.warning(f"⚠️ 发现 {total_issues} 个不一致项，开始自动修复...")
            logger.warning(f"  - Mismatched: {len(mismatched_codes)}")
            logger.warning(f"  - Missing in CH: {len(missing_in_ch)}")
            logger.warning(f"  - Missing in MySQL: {len(missing_in_mysql)}")
            
            # 3.1 修复 Mismatched & Missing in CH: 重做这些股票
            stocks_to_resync = list(mismatched_codes | missing_in_ch)
            if stocks_to_resync:
                await self._heal_by_resync(stocks_to_resync)
            
            # 3.2 修复 Missing in MySQL: 删除 ClickHouse 中多余的数据 (脏数据)
            if missing_in_mysql:
                await self._delete_orphaned_stocks(list(missing_in_mysql))
            
            duration = (datetime.now() - start_time).total_seconds()
            msg = f"🛡️ 审计并修复完成。修复不一致:{len(stocks_to_resync)}, 清理孤儿:{len(missing_in_mysql)}"
            logger.info(msg)
            await self.sync_service._log_to_db("SUCCESS", len(stocks_to_resync), msg, duration, task_name="weekly_deep_audit")
            
        except Exception as e:
            logger.error(f"❌ 审计任务失败: {e}", exc_info=True)
            await self.sync_service._log_to_db("FAILED", 0, str(e), (datetime.now() - start_time).total_seconds(), task_name="weekly_deep_audit")
            raise e

    async def _get_mysql_fingerprints(self) -> Dict[str, Fingerprint]:
        """获取 MySQL 全量指纹"""
        logger.info("正在计算 MySQL 指纹...")
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 必须转为 int/float 以统一比较，ClickHouse sum(volume) 可能是 float
                query = "SELECT code, COUNT(*), SUM(volume) FROM stock_kline_daily GROUP BY code"
                await cursor.execute(query)
                rows = await cursor.fetchall()
                # rows is list of tuples (code, count, volume)
                fp = {}
                for r in rows:
                    code = r[0]
                    count = r[1]
                    volume = float(r[2]) if r[2] is not None else 0.0
                    fp[code] = Fingerprint(count, volume)
                logger.info(f"MySQL 指纹计算完成: {len(fp)} 只股票")
                return fp

    async def _get_clickhouse_fingerprints(self) -> Dict[str, Fingerprint]:
        """获取 ClickHouse 全量指纹"""
        logger.info("正在计算 ClickHouse 指纹...")
        async with self.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = """
                    SELECT stock_code, count(), sum(volume) 
                    FROM stock_kline_daily 
                    GROUP BY stock_code
                """
                await cursor.execute(query)
                rows = await cursor.fetchall()
                fp = {}
                for r in rows:
                    code = r[0]
                    count = r[1]
                    volume = float(r[2]) if r[2] is not None else 0.0
                    fp[code] = Fingerprint(count, volume)
                logger.info(f"ClickHouse 指纹计算完成: {len(fp)} 只股票")
                return fp

    def _compare_fingerprints(self, mysql_fp: Dict[str, Fingerprint], ch_fp: Dict[str, Fingerprint]) -> Tuple[set, set, set]:
        """
        对比指纹
        Returns:
            (mismatched_codes, missing_in_ch, missing_in_mysql)
        """
        mysql_codes = set(mysql_fp.keys())
        ch_codes = set(ch_fp.keys())
        
        missing_in_ch = mysql_codes - ch_codes
        missing_in_mysql = ch_codes - mysql_codes
        
        common_codes = mysql_codes & ch_codes
        mismatched = set()
        
        for code in common_codes:
            mf = mysql_fp[code]
            cf = ch_fp[code]
            
            # 比较 Count 和 Volume
            # Volume 可能是浮点数，允许微小误差 (e.g. 0.01) 虽然 volume 通常是整数
            if mf.count != cf.count or abs(mf.volume_sum - cf.volume_sum) > self.VOLUME_TOLERANCE:
                logger.warning(f"Mismatch {code}: MySQL({mf}) vs CH({cf})")
                mismatched.add(code)
                
        return mismatched, missing_in_ch, missing_in_mysql

    async def _heal_by_resync(self, codes: List[str]):
        """
        修复指定股票: 删除本地数据 -> 重新同步
        """
        logger.info(f"正在修复 {len(codes)} 只股票数据...")
        
        # 1. Delete from ClickHouse
        # Split into batches to avoid huge SQL
        for i in range(0, len(codes), self.BATCH_SIZE):
            batch = codes[i:i+self.BATCH_SIZE]
            
            try:
                async with self.clickhouse_pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        # Use tuple format for safe parameterization
                        # ClickHouse asynch doesn't support %s for IN clause, use manual escaping
                        # Escape single quotes by doubling them
                        safe_codes = [code.replace("'", "''") for code in batch]
                        formatted_codes = ",".join([f"'{c}'" for c in safe_codes])
                        query = f"ALTER TABLE stock_kline_daily DELETE WHERE stock_code IN ({formatted_codes})"
                        await cursor.execute(query)
            except Exception as e:
                logger.error(f"Failed to delete batch starting at index {i}: {e}")
                raise
            
        # 2. Resync
        # sync_by_stock_codes handles logging and insertion
        await self.sync_service.sync_by_stock_codes(codes)
        logger.info(f"✓ 已重新同步 {len(codes)} 只股票")

    async def _delete_orphaned_stocks(self, codes: List[str]):
        """删除 ClickHouse 中存在但 MySQL 中不存在的孤儿股票"""
        logger.info(f"正在清理 {len(codes)} 只孤儿股票...")
        for i in range(0, len(codes), self.BATCH_SIZE):
            batch = codes[i:i+self.BATCH_SIZE]
            
            try:
                async with self.clickhouse_pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        # Escape single quotes for safety
                        safe_codes = [code.replace("'", "''") for code in batch]
                        formatted_codes = ",".join([f"'{c}'" for c in safe_codes])
                        query = f"ALTER TABLE stock_kline_daily DELETE WHERE stock_code IN ({formatted_codes})"
                        await cursor.execute(query)
            except Exception as e:
                logger.error(f"Failed to delete orphaned batch starting at index {i}: {e}")
                raise
        logger.info(f"✓ 已清理 {len(codes)} 只孤儿股票")
