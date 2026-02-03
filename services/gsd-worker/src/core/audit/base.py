import logging
import json
from typing import List, Optional, Set, Dict, Any
from datetime import datetime
import pytz
from core.tick_sync_service import TickSyncService

logger = logging.getLogger("AuditBase")
CST = pytz.timezone('Asia/Shanghai')

class BaseAuditor:
    def __init__(self, target_date: str, stock_codes: Optional[List[str]] = None, threshold: Optional[int] = None):
        self.service = TickSyncService()
        self.target_date = self._normalize_date(target_date)
        self.stock_codes = stock_codes
        self.threshold = threshold
        
    def _normalize_date(self, date_str: str) -> str:
        """归一化日期 YYYYMMDD 或 YYYY-MM-DD -> YYYY-MM-DD"""
        if date_str and "-" not in date_str and len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        return date_str

    async def initialize(self):
        await self.service.initialize()
        
    async def close(self):
        await self.service.close()

    def _normalize_code(self, raw_code: str) -> str:
        """归一化股票代码到 6 位"""
        code = raw_code.upper()
        if code.endswith(('.SZ', '.SH', '.BJ')):
            return code.split('.')[0]
        if code.startswith(('SZ.', 'SH.', 'BJ.')):
            return code.split('.')[1]
        return code

    async def get_target_scope(self) -> Set[str]:
        """确定审计目标范围 (过滤北证)"""
        # Priority 1: User specified stock codes
        if self.stock_codes:
            all_codes = self.stock_codes
        else:
            # Priority 2: From Redis sync_list
            all_codes = await self.service.fetch_sync_list(scope="all", trade_date=self.target_date)
            
        if not all_codes:
            logger.warning("fetch_sync_list returned empty. Attempting Fallback to ClickHouse Kline...")
            async with self.service.clickhouse_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"SELECT DISTINCT stock_code FROM stock_data.stock_kline_daily WHERE trade_date = '{self.target_date}'")
                    rows = await cursor.fetchall()
                    all_codes = list(set([self._normalize_code(r[0]) for r in rows]))
            
        if not all_codes:
            logger.error("❌ Failed to get target scope.")
            return set()

        # Filter BJ for standard audit
        target_scope = set()
        for code in all_codes:
            normalized = self._normalize_code(code)
            if normalized.startswith(('4', '8', '9')):
                continue
            target_scope.add(normalized)
            
        logger.info(f"🎯 目标范围: 总数={len(all_codes)} -> 过滤非法/北证后={len(target_scope)}")
        return target_scope

    def print_gsd_output(self, output: Dict[str, Any]):
        """统一打印 GSD_OUTPUT_JSON，供 Orchestrator 捕获"""
        print(f"\n---GSD_START---\nGSD_OUTPUT_JSON: {json.dumps(output)}\n---GSD_END---", flush=True)
