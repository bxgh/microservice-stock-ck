#!/usr/bin/env python3
"""
盘后分笔数据审计与自愈作业 (Audit Tick Resilience)
Implemented per Post-Market Audit Workflow V4.0 (Precise Edition)
"""

import asyncio
import logging
import sys
import os
import argparse
from datetime import datetime
from typing import List, Optional, Dict, Any
import pytz
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.tick_sync_service import TickSyncService
from gsd_shared.validation.standards import TickStandards

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
        """Step 1: 确定目标范围"""
        if self.stock_codes:
            all_codes = self.stock_codes
        else:
            all_codes = await self.service.fetch_sync_list(scope="all", trade_date=self.target_date)
            
        if not all_codes:
            logger.error("❌ Failed to get target scope.")
            return set()

        target_scope = set()
        for code in all_codes:
            normalized = self._normalize_code(code)
            # 过滤北证
            if normalized.startswith(('4', '8', '9')):
                continue
            target_scope.add(normalized)
            
        logger.info(f"🎯 目标范围: 总数={len(all_codes)} -> 过滤非法/北证后={len(target_scope)}")
        return target_scope

    def _normalize_code(self, raw_code: str) -> str:
        code = str(raw_code).upper()
        if code.endswith(('.SZ', '.SH', '.BJ')):
            return code.split('.')[0]
        if code.startswith(('SZ.', 'SH.', 'BJ.')):
            return code.split('.')[1]
        return code

    async def execute_validation(self, target_scope: set):
        """Step 3: 高速内存对账 (Snapshot First -> Kline Fallback)"""
        logger.info(f"🚀 开始精准审计对账 (Session={self.session}, Mode=Precise)...")
        
        today_str = datetime.now(CST).strftime("%Y-%m-%d")
        sql_date = self.target_date
        if len(sql_date) == 8:
            sql_date = f"{sql_date[:4]}-{sql_date[4:6]}-{sql_date[6:]}"
        
        target_table = "tick_data_intraday" if sql_date == today_str else "tick_data"

        # 1. Load Ticks (Batch)
        tick_map = {}
        async with self.service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                logger.info(f"   -> Loading Tick Data from {target_table}...")
                await cursor.execute(f"""
                    SELECT stock_code, sum(volume), argMax(price, tick_time), max(tick_time)
                    FROM {target_table}
                    WHERE trade_date = '{sql_date}'
                    GROUP BY stock_code
                """)
                rows = await cursor.fetchall()
                for r in rows:
                    tick_map[r[0]] = {
                        'vol': float(r[1]), 
                        'price': float(r[2]),
                        'last_time': str(r[3])
                    }
        
        # 2. Load Snapshots (Batch) - Snapshot First
        snap_map = {}
        min_snap_time = TickStandards.Precise.SNAPSHOT_MIN_TIME_NOON if self.session == "noon" else TickStandards.Precise.SNAPSHOT_MIN_TIME_CLOSE
        
        async with self.service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                logger.info("   -> Loading Snapshot Data (Golden Reference)...")
                # 为每只股票获取符合时间要求的最后一条快照
                await cursor.execute(f"""
                    SELECT stock_code, total_volume, current_price, snapshot_time
                    FROM stock_data.snapshot_data_distributed
                    WHERE trade_date = '{sql_date}'
                      AND formatDateTime(snapshot_time, '%%H:%%M:%%S') >= '{min_snap_time}'
                    ORDER BY stock_code, snapshot_time DESC
                    LIMIT 1 BY stock_code
                """)
                rows = await cursor.fetchall()
                for r in rows:
                    snap_map[r[0]] = {
                        'vol': float(r[1]), 
                        'close': float(r[2]),
                        'time': str(r[3])
                    }

        # 3. Load KLines (Batch) - Fallback
        kline_map = {}
        async with self.service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                logger.info("   -> Loading KLine Data (Fallback Reference)...")
                await cursor.execute(f"""
                    SELECT stock_code, volume, close_price
                    FROM stock_data.stock_kline_daily
                    WHERE trade_date = '{sql_date}'
                """)
                rows = await cursor.fetchall()
                for r in rows:
                    std_code = self._normalize_code(r[0])
                    kline_map[std_code] = {
                        'vol': float(r[1]), 
                        'close': float(r[2])
                    }

        # 4. Compare
        missing_list = []
        invalid_list = []
        valid_cnt = 0
        
        for code in target_scope:
            if code not in tick_map:
                missing_list.append(code)
                continue
                
            t_data = tick_map[code]
            
            # Determine reference
            ref_source = "snapshot"
            ref_data = snap_map.get(code)
            
            if not ref_data:
                ref_data = kline_map.get(code)
                ref_source = "kline"
            
            if not ref_data:
                # No reference available, skip specific check but count as valid for now (or warning)
                valid_cnt += 1
                continue
            
            reasons = []
            
            # Price Compare (Precise: <= 0.1)
            price_diff = abs(t_data['price'] - ref_data['close'])
            if price_diff > TickStandards.Precise.PRICE_TOLERANCE:
                reasons.append(f"Price: {t_data['price']} vs {ref_data['close']} (Diff={price_diff:.4f})")
            
            # Volume Compare (Precise: <= 0.5%)
            vol_diff_abs = abs(t_data['vol'] - ref_data['vol'])
            vol_diff_pct = vol_diff_abs / ref_data['vol'] if ref_data['vol'] > 0 else 0
            
            if ref_data['vol'] > 0 and vol_diff_pct > TickStandards.Precise.VOLUME_TOLERANCE:
                reasons.append(f"Volume: {t_data['vol']} vs {ref_data['vol']} (Diff={vol_diff_pct:.2%})")
            elif ref_data['vol'] == 0 and t_data['vol'] > 0:
                reasons.append(f"Volume: {t_data['vol']} vs 0")

            if reasons:
                invalid_list.append({
                    'code': code,
                    'reasons': reasons,
                    'source': ref_source,
                    'vol_diff_abs': vol_diff_abs
                })
                continue
            
            valid_cnt += 1

        # Summary and Diagnosis
        output = {
            "target_date": self.target_date,
            "session": self.session,
            "stats": {
                "total_expected": len(target_scope),
                "valid": valid_cnt,
                "missing": len(missing_list),
                "bad_quality": len(invalid_list)
            },
            # 汇总缺失和质量差的代码用于补采
            "missing_list": missing_list + [i['code'] for i in invalid_list],
            "details": invalid_list[:10], # 只保留前10个详情
            "diagnosis": {
                "action": "AI_AUDIT" if (len(missing_list) + len(invalid_list)) <= 200 else "FAILOVER",
                "reason": f"Audit found {len(missing_list)} missing and {len(invalid_list)} bad quality stocks"
            }
        }
        
        if (len(missing_list) + len(invalid_list)) == 0:
            output["diagnosis"]["action"] = "NONE"

        return output

    async def run(self):
        try:
            # Normalize date
            clean_date = self.target_date.replace("-", "")
            self.target_date = clean_date

            await self.initialize()
            try:
                target_scope = await self.get_target_scope()
                if not target_scope:
                    return
                
                output = await self.execute_validation(target_scope)
                # JSON output for orchestrator
                print(f"\n---GSD_START---\nGSD_OUTPUT_JSON: {json.dumps(output)}\n---GSD_END---", flush=True)
            finally:
                await self.close()
            
        except Exception as e:
            logger.error(f"❌ 审计任务异常: {e}", exc_info=True)
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="分笔数据精准审计入口 (Precise Edition)")
    parser.add_argument("--date", type=str, help="审计日期 (YYYYMMDD)")
    parser.add_argument("--session", type=str, choices=["noon", "close"], default="close", help="审计时段")
    parser.add_argument("--threshold", type=float, help="故障阈值 (保留参数)")
    parser.add_argument("--stock-codes", type=str, help="手动指定审计列表 (逗号分隔)")
    args = parser.parse_args()
    
    codes = args.stock_codes.split(",") if args.stock_codes else None
    job = AuditJob(target_date=args.date, stock_codes=codes, session=args.session, threshold=args.threshold)
    
    asyncio.run(job.run())
