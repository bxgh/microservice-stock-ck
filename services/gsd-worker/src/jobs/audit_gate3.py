#!/usr/bin/env python3
"""
盘后一致性审计 (Gate-3 Audit)
对比 MySQL K线成交量与 ClickHouse 分笔成交量
"""

import asyncio
import logging
import sys
import os
import argparse
import json
from datetime import datetime
import pytz

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.tick_sync_service import TickSyncService
from gsd_shared.validation.standards import TickStandards
from gsd_shared.tick.utils import clean_stock_code

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("AuditGate3")
CST = pytz.timezone('Asia/Shanghai')

class AuditGate3Job:
    def __init__(self, target_date: str):
        self.service = TickSyncService()
        # 标准化日期 YYYYMMDD
        self.target_date = target_date.replace("-", "").replace("/", "")
        # MySQL 格式 YYYY-MM-DD
        self.sql_date = f"{self.target_date[:4]}-{self.target_date[4:6]}-{self.target_date[6:]}"

    async def run(self):
        await self.service.initialize()
        
        # Initialize MySQL pool (TickSyncService has config but no pool)
        import aiomysql
        mysql_pool = await aiomysql.create_pool(
            **self.service.mysql_config,
            minsize=1,
            maxsize=5
        )
        
        try:
            logger.info(f"🚀 开始盘后 Gate-3 审计: 日期={self.target_date}")
            
            # 1. 获取 MySQL K线成交量 (作为基准)
            # 单位：手 -> 股 (x100)
            kline_map = {}
            async with mysql_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        SELECT ts_code, volume 
                        FROM stock_kline_daily 
                        WHERE trade_date = %s
                    """, (self.sql_date,))
                    rows = await cursor.fetchall()
                    for code, vol in rows:
                        # 过滤非 A 股 (比如指数，虽然代码里可能已经过滤了)
                        clean_code = clean_stock_code(code)
                        kline_map[clean_code] = float(vol)
            
            if not kline_map:
                logger.warning(f"⚠️ MySQL 中未发现日期 {self.target_date} 的 K 线数据，审计中止。")
                return

            # 2. 获取 ClickHouse Tick 成交量
            tick_map = {}
            async with self.service.clickhouse_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 使用分布式表进行全量审计, 必须带 FINAL
                    await cursor.execute(f"""
                        SELECT ts_code, sum(volume) 
                        FROM stock_data.tick_data FINAL
                        WHERE trade_date = '{self.sql_date}'
                        GROUP BY ts_code
                    """)
                    rows = await cursor.fetchall()
                    for code, vol in rows:
                        tick_map[code] = float(vol)

            # 3. 对比分析
            failed_stocks = []
            valid_count = 0
            missing_count = 0
            
            threshold = TickStandards.Precise.VOLUME_TOLERANCE  # 0.5%
            
            for code, expected_vol in kline_map.items():
                actual_vol = tick_map.get(code, 0)
                
                if actual_vol == 0:
                    missing_count += 1
                    failed_stocks.append({
                        "code": code,
                        "expected": expected_vol,
                        "actual": 0,
                        "diff_pct": 100.0,
                        "reason": "Missing Data"
                    })
                    continue

                if expected_vol == 0:
                    if actual_vol == 0:
                        valid_count += 1
                    else:
                        failed_stocks.append({
                            "code": code,
                            "expected": 0,
                            "actual": actual_vol,
                            "diff_pct": 100.0,
                            "reason": "Unexpected Data (KLine Vol is 0)"
                        })
                    continue
                
                diff_pct = abs(actual_vol - expected_vol) / expected_vol
                
                if diff_pct > threshold:
                    failed_stocks.append({
                        "code": code,
                        "expected": expected_vol,
                        "actual": actual_vol,
                        "diff_pct": round(diff_pct * 100, 4),
                        "reason": f"Volume Mismatch > {threshold*100}%"
                    })
                    if len(failed_stocks) <= 5:
                        logger.info(f"🔍 Mismatch {code}: MySQL={expected_vol:.0f}, CH={actual_vol:.0f}, Diff={diff_pct*100:.2f}%")
                else:
                    valid_count += 1

            # 4. 汇总输出
            output = {
                "date": self.target_date,
                "stats": {
                    "total_kline": len(kline_map),
                    "total_tick": len(tick_map),
                    "valid": valid_count,
                    "missing": missing_count,
                    "mismatch": len(failed_stocks) - missing_count,
                    "failed_total": len(failed_stocks)
                },
                "threshold_pct": threshold * 100,
                "failed_count": len(failed_stocks),
                "failed_list": ",".join([s["code"] for s in failed_stocks]),
                "missing_list": [s["code"] for s in failed_stocks if s["actual"] == 0],
                "mismatch_list": [s["code"] for s in failed_stocks if s["actual"] > 0],
                "top_failures": failed_stocks[:10]
            }
            
            # 打印结构化输出供 Orchestrator 捕获
            print(f"\n---GSD_START---\nGSD_OUTPUT_JSON: {json.dumps(output)}\n---GSD_END---", flush=True)
            
            logger.info(f"✅ 审计完成: 总计={len(kline_map)}, 成功={valid_count}, 失败={len(failed_stocks)} (缺失={missing_count})")
            
        except Exception as e:
            logger.error(f"❌ 审计任务执行失败: {e}", exc_info=True)
            sys.exit(1)
        finally:
            mysql_pool.close()
            await mysql_pool.wait_closed()
            await self.service.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gate-3 盘后分笔数据审计")
    parser.add_argument("--date", type=str, help="审计日期 (YYYYMMDD)")
    args = parser.parse_args()
    
    target_date = args.date or datetime.now(CST).strftime("%Y%m%d")
    asyncio.run(AuditGate3Job(target_date).run())
