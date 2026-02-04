
#!/usr/bin/env python3
"""
盘后分笔数据审计与自愈作业 (Audit Tick Resilience)
Implemented per Post-Market Audit Workflow V2
"""

import asyncio
import logging
import sys
import os
import argparse
from datetime import datetime
from typing import List, Optional
import pytz
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.tick_sync_service import TickSyncService

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("AuditTickResilience")
CST = pytz.timezone('Asia/Shanghai')


class AuditJob:
    def __init__(self, target_date: Optional[str] = None, stock_codes: Optional[List[str]] = None, session: str = "close", threshold: Optional[float] = None):
        self.service = TickSyncService()
        self.target_date = target_date or datetime.now(CST).strftime("%Y-%m-%d")
        self.stock_codes = stock_codes
        self.session = session
        self.threshold = threshold
        
    async def initialize(self):
        await self.service.initialize()
        
    async def close(self):
        await self.service.close()

    async def get_target_scope(self) -> set:
        """Step 1: 确定目标范围 (Exclude BJ)"""
        # Priority 1: User specified stock codes
        if self.stock_codes:
            all_codes = self.stock_codes
        else:
            # Priority 2: From Redis sync_list (V4.0 - Auto filter suspended)
            all_codes = await self.service.fetch_sync_list(scope="all", trade_date=self.target_date)
            
        if not all_codes:
            logger.warning("fetch_sync_list returned empty. (Redis empty?) Attempting Fallback to ClickHouse Kline...")
            sql_date = self.target_date
            if "-" not in sql_date and len(sql_date) == 8:
                sql_date = f"{sql_date[:4]}-{sql_date[4:6]}-{sql_date[6:]}"
                
            async with self.service.clickhouse_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"SELECT DISTINCT stock_code FROM stock_data.stock_kline_daily WHERE trade_date = '{sql_date}'")
                    rows = await cursor.fetchall()
                    all_codes = list(set([self._normalize_code(r[0]) for r in rows]))
            
        if not all_codes:
            logger.error("❌ Failed to get target scope.")
            return set()

        # Filter BJ for standard audit
        target_scope = set()
        for code in all_codes:
            normalized = self._normalize_code(code)
            # 统一北证过滤规则: 4/8/9 前缀
            if normalized.startswith(('4', '8', '9')):
                continue
            target_scope.add(normalized)
            
        logger.info(f"🎯 目标范围: 总数={len(all_codes)} -> 过滤非法/北证后={len(target_scope)}")
        return target_scope

    async def check_dependency(self, target_scope: set) -> bool:
        """Step 2: K线就绪检查"""
        expected_count = len(target_scope)
        if expected_count == 0:
            return False

        async with self.service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # Query KLine count for target date
                # We only count codes that appear in our target_scope
                # But for performance we just count total excluding BJ
                sql_date = self.target_date
                if "-" not in sql_date and len(sql_date) == 8:
                    sql_date = f"{sql_date[:4]}-{sql_date[4:6]}-{sql_date[6:]}"
                    
                await cursor.execute(f"""
                    SELECT count() 
                    FROM stock_data.stock_kline_daily 
                    WHERE trade_date = '{sql_date}'
                    AND stock_code NOT LIKE 'bj.%' 
                    AND stock_code NOT LIKE '%.BJ'
                    AND stock_code NOT LIKE 'sh.8%%'
                    AND stock_code NOT LIKE 'sz.8%%'
                """)
                row = await cursor.fetchone()
                actual_count = row[0] if row else 0

        coverage = actual_count / expected_count
        logger.info(f"🏗️  K线就绪检查: 实际={actual_count}/预期={expected_count} (覆盖率={coverage:.2%})")

        if coverage < 1.0:
            logger.error("❌ K线数据未就绪! (Threshold 100%)")
            # For strict mode, we might want to return False, but let's see actual counts first.
            if coverage < 1.0:
                 return False
            # Check if we have SOME data to proceed for demonstration?
            # User said: NO DEGRADE. So return False.
            return False
            
        return True

    def _normalize_code(self, raw_code: str) -> str:
        """
        Normalize stock code to 6 digits.
        Handles: sh.600000, 600000.SH, 600000
        """
        code = raw_code.upper()
        if code.endswith(('.SZ', '.SH', '.BJ')):
            return code.split('.')[0]
        if code.startswith(('SZ.', 'SH.', 'BJ.')):
            return code.split('.')[1]
        return code

    async def execute_validation(self, target_scope: set):
        """Step 3: 高速内存对账 (盘后/全天)"""
        logger.info("🚀 开始盘后高速内存对账...")
        
        today_str = datetime.now(CST).strftime("%Y-%m-%d")
        target_table = "tick_data_intraday" if self.target_date == today_str else "tick_data"
        
        # 1. Load Ticks (Batch)
        tick_map = {}
        async with self.service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                logger.info(f"   -> Loading Tick Data from {target_table}...")
                sql_date = self.target_date
                if "-" not in sql_date and len(sql_date) == 8:
                    sql_date = f"{sql_date[:4]}-{sql_date[4:6]}-{sql_date[6:]}"
                    
                await cursor.execute(f"""
                    SELECT stock_code, count(), sum(volume), sum(amount), argMax(price, tick_time)
                    FROM {target_table} FINAL
                    WHERE trade_date = '{sql_date}'
                      AND tick_time <= '15:00:00'
                    GROUP BY stock_code
                """)
                rows = await cursor.fetchall()
                for r in rows:
                    tick_map[r[0]] = {
                        'count': r[1], 
                        'vol': float(r[2]), 
                        'amt': float(r[3]) if r[3] is not None else 0.0,
                        'price': float(r[4])
                    }
        
        logger.info(f"   -> Loaded {len(tick_map)} tick records.")

        # 2. Load KLines (Batch)
        kline_map = {}
        async with self.service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                logger.info("   -> Loading KLine Data...")
                sql_date = self.target_date
                if "-" not in sql_date and len(sql_date) == 8:
                    sql_date = f"{sql_date[:4]}-{sql_date[4:6]}-{sql_date[6:]}"
                    
                await cursor.execute(f"""
                    SELECT stock_code, volume, amount, close_price
                    FROM stock_data.stock_kline_daily
                    WHERE trade_date = '{sql_date}'
                """)
                rows = await cursor.fetchall()
                for r in rows:
                    std_code = self._normalize_code(r[0])
                    kline_map[std_code] = {
                        'vol': float(r[1]), 
                        'amt': float(r[2]) if r[2] is not None else 0.0,
                        'close': float(r[3])
                    }
        
        logger.info(f"   -> Loaded {len(kline_map)} kline records.")

        # 3. Compare
        missing_list = []
        invalid_list = []
        valid_cnt = 0
        
        for code in target_scope:
            if code not in tick_map:
                missing_list.append(code)
                continue
            
            if code not in kline_map:
                continue
                
            t_data = tick_map[code]
            k_data = kline_map[code]
            
            price_diff = abs(t_data['price'] - k_data['close'])
            amt_diff_abs = abs(t_data['amt'] - k_data['amt'])

            if price_diff > 0.01:
                invalid_list.append({
                    'code': code, 
                    'reason': f"Price Mismatch ({t_data['price']} vs {k_data['close']})",
                    'amt_diff': amt_diff_abs
                })
                continue
                
            vol_diff_pct = 0
            if k_data['vol'] > 0:
                vol_diff_pct = abs(t_data['vol'] - k_data['vol']) / k_data['vol']
                
            amt_diff_pct = 0
            if k_data['amt'] > 0:
                amt_diff_pct = abs(t_data['amt'] - k_data['amt']) / k_data['amt']

            if vol_diff_pct > 0.02 or amt_diff_pct > 0.02:
                invalid_list.append({
                    'code': code,
                    'reason': f"Vol/Amt Mismatch ({vol_diff_pct:.1%})",
                    'amt_diff': amt_diff_abs,
                    'vol_diff_pct': vol_diff_pct
                })
                continue
            
            valid_cnt += 1

        output = {
            "target_date": self.target_date,
            "stats": {
                "valid": valid_cnt,
                "missing": len(missing_list),
                "heavy_fault": len([i for i in invalid_list if i['amt_diff'] >= 100000]),
                "light_fault": len([i for i in invalid_list if i['amt_diff'] < 100000])
            },
            "missing_list": missing_list + [i['code'] for i in invalid_list if i['amt_diff'] >= 100000],
            "abnormal_list": [i['code'] for i in invalid_list if i['amt_diff'] < 100000],
            "diagnosis": {
                "action": "AI_AUDIT" if (len(missing_list) + len(invalid_list)) <= 200 else "FAILOVER"
            }
        }
        if (len(missing_list) + len(invalid_list)) == 0:
            output["diagnosis"]["action"] = "NONE"

        return output

    async def run(self):
        try:
            # 归一化日期
            if self.target_date and "-" in self.target_date:
                self.target_date = self.target_date.replace("-", "")

            # 路由到具体的审计器
            if self.session == "noon":
                from core.audit.noon_auditor import NoonAuditor
                logger.info(f"🎯 路由至 NoonAuditor (午间审计模式)")
                auditor = NoonAuditor(target_date=self.target_date, stock_codes=self.stock_codes, threshold=self.threshold)
                await auditor.initialize()
                try:
                    output = await auditor.run()
                    auditor.print_gsd_output(output)
                finally:
                    await auditor.close()
            else:
                # 默认/盘后审计模式 (保留原有逻辑)
                await self.initialize()
                try:
                    target_scope = await self.get_target_scope()
                    if not target_scope:
                        return
                    
                    # 只有盘后审计需要检查 K 线依赖
                    is_ready = await self.check_dependency(target_scope)
                    if not is_ready:
                        logger.error("Dependency Check Failed. ABORTING.")
                        sys.exit(1)
                        
                    output = await self.execute_validation(target_scope)
                    # 统一输出
                    print(f"\n---GSD_START---\nGSD_OUTPUT_JSON: {json.dumps(output)}\n---GSD_END---", flush=True)
                finally:
                    await self.close()
            
        except Exception as e:
            logger.error(f"❌ 审计任务异常: {e}", exc_info=True)
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="分笔数据审计入口 (Gate-Noon/Gate-3)")
    parser.add_argument("--date", type=str, help="审计日期 (YYYYMMDD)")
    parser.add_argument("--session", type=str, choices=["noon", "close"], default="close", help="审计时段")
    parser.add_argument("--threshold", type=float, help="故障阈值")
    parser.add_argument("--stock-codes", type=str, help="手动指定审计列表 (逗号分隔)")
    args = parser.parse_args()
    
    codes = args.stock_codes.split(",") if args.stock_codes else None
    job = AuditJob(target_date=args.date, stock_codes=codes, session=args.session, threshold=args.threshold)
    
    asyncio.run(job.run())

