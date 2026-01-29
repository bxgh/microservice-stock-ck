#!/usr/bin/env python3
"""
Job: audit_tick_resilience.py
功能：盘后分笔数据韧性审计 (Traffic Cop 2.0)
职责：
1. 确定审计日期 (6:00 AM 规则)
2. 加载全市场预期 A 股名单 (StockUniverse)
3. 深度审计 ClickHouse分笔连续性 (09:25-15:00, 241分钟)
4. 实现智能分级路由 (Green/Yellow/Red)
5. 输出 GSD_OUTPUT_JSON 供编排器决策
"""

import asyncio
import logging
import sys
import json
import argparse
from datetime import datetime, timedelta
import pytz
from core.tick_sync_service import TickSyncService
from gsd_shared.validation.standards import TickStandards

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DataQualityAudit")
CST = pytz.timezone('Asia/Shanghai')

async def main():
    parser = argparse.ArgumentParser(description="盘后数据深度审计 (韧性决策)")
    parser.add_argument("--date", type=str, help="YYYYMMDD")
    parser.add_argument("--threshold", type=int, default=1000, help="异常阈值 (行数，仅作参考)")
    args = parser.parse_args()

    service = TickSyncService()
    await service.initialize()

    try:
        # 0. 确定审计日期 (对接 Gate-3 规范)
        if args.date:
            try:
                dt = datetime.strptime(args.date, "%Y%m%d")
                trade_date = dt.strftime("%Y-%m-%d")
            except ValueError:
                trade_date = args.date
        else:
            now = datetime.now(CST)
            if now.hour < 6:
                target_date = now - timedelta(days=1)
                logger.info(f"⏰ 当前时间 {now.strftime('%H:%M')} < 06:00，审计前一交易日")
            else:
                target_date = now
            trade_date = target_date.strftime("%Y-%m-%d")

        logger.info(f"️ 开始深度审计 (Level 1-3): {trade_date}")

        # 1. 加载预期名单 (Inventory)
        # 获取全市场 A 股名单
        expected_codes = await service.stock_universe.get_all_a_stocks()
        expected_count = len(expected_codes)
        logger.info(f"📋 预期 A 股总数: {expected_count}")

        if expected_count == 0:
            logger.error("❌ 无法获取预期股票名单，审计无法进行")
            sys.exit(1)

        # 2. 联合查询 ClickHouse: Tick指标 + K线对账指标
        # 整合 L1, L2, L3 需要的所有字段
        # L3 依赖 stock_kline_daily 进行对账
        
        query = f"""
        SELECT 
            t.stock_code,
            t.tick_count,
            t.first_tick,
            t.last_tick,
            t.active_minutes,
            t.total_volume,
            t.last_price,
            k.close_price as kline_close,
            k.volume as kline_volume
        FROM (
            SELECT 
                stock_code,
                count() as tick_count,
                min(tick_time) as first_tick,
                max(tick_time) as last_tick,
                countDistinct(substring(tick_time, 1, 5)) as active_minutes,
                sum(volume) as total_volume,
                argMax(price, tick_time) as last_price
            FROM stock_data.tick_data_intraday 
            WHERE trade_date = '{trade_date}'
            GROUP BY stock_code
        ) AS t
        LEFT JOIN (
            SELECT stock_code, close_price, volume
            FROM stock_data.stock_kline_daily
            WHERE trade_date = '{trade_date}'
        ) AS k ON t.stock_code = k.stock_code
        """
        
        async with service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query)
                rows = await cursor.fetchall()
        
        # 3. 深度多维分析 (L1-L3)
        actual_data = {row[0]: row for row in rows}
        logger.info(f"📉 实际 Tick 入库股票数: {len(actual_data)}")

        missing_list = []      # L1 缺失
        abnormal_list = []     # L2/L3 异常
        
        std = TickStandards.IntradayPostMarket
        
        for code in expected_codes:
            # --- Level 1: Existence ---
            if code not in actual_data:
                missing_list.append(code)
                continue
            
            # --- 解析指标 ---
            # row: [code, count, first, last, active, sum_vol, last_p, k_close, k_vol]
            _, count, first_t, last_t, active_m, sum_vol, last_p, k_close, k_vol = actual_data[code]
            
            is_abnormal = False
            reasons = []
            error_level = None

            # --- Level 2: Completeness (结构性检查) ---
            f_cmp = first_t if len(first_t) == 8 else f"{first_t}:00"
            l_cmp = last_t if len(last_t) == 8 else f"{last_t}:00"
            
            if active_m < std.MIN_ACTIVE_MINUTES:
                is_abnormal = True
                error_level = "L2"
                reasons.append(f"时长不足({active_m}/{std.MIN_ACTIVE_MINUTES})")
            
            if f_cmp > std.MIN_TIME:
                is_abnormal = True
                error_level = "L2"
                reasons.append(f"开盘晚({first_t})")
                
            if l_cmp < std.MAX_TIME:
                is_abnormal = True
                error_level = "L2"
                reasons.append(f"收盘早({last_t})")

            # --- Level 3: Accuracy (数据对账检查) ---
            if not is_abnormal and k_close is not None:
                # 1. 价格对账 (容忍 0.015 误差)
                if abs(last_p - k_close) > 0.015:
                    is_abnormal = True
                    error_level = "L3"
                    reasons.append(f"价格不匹配(Tick:{last_p}/K:{k_close})")
                
                # 2. 成交量对账 (容忍 5% 误差, 文档要求)
                if k_vol and k_vol > 0:
                    vol_diff = abs(sum_vol - k_vol) / k_vol
                    if vol_diff > 0.05:
                        is_abnormal = True
                        error_level = "L3"
                        reasons.append(f"成交量差额大({vol_diff:.1%})")

            # 行数硬性兜底 (args.threshold)
            if not is_abnormal and count < args.threshold:
                is_abnormal = True
                error_level = "L2" 
                reasons.append(f"Tick太稀疏({count})")

            if is_abnormal:
                abnormal_list.append({
                    "code": code,
                    "level": error_level,
                    "count": count,
                    "active_minutes": active_m,
                    "first_tick": first_t,
                    "last_tick": last_t,
                    "reason": ",".join(reasons)
                })

        missing_count = len(missing_list)
        abnormal_count = len(abnormal_list)
        missing_rate = missing_count / expected_count if expected_count > 0 else 0.0
        abnormal_rate = abnormal_count / expected_count if expected_count > 0 else 0.0

        # 4. 智能路由 (The Traffic Cop 2.0 Logic)
        action_recommendation = "NONE"
        failover_mode = False

        logger.info(f"🚦 审计摘要: 缺失(L1)={missing_count}, 异常(L2/L3)={abnormal_count}")
        logger.info(f"📊 质量指标: 缺失率={missing_rate:.2%}, 异常率={abnormal_rate:.2%}")

        if missing_rate < 0.01 and abnormal_rate < 0.05:
            logger.info("🟢 Zone 1 (Green): 质量达标，无需自动修复")
            action_recommendation = "NONE"
        elif missing_rate < 0.10 and abnormal_rate < 0.10:
            logger.info("🟡 Zone 2 (Yellow): 触发 AI 深度定性门禁")
            action_recommendation = "AI_AUDIT"
            
            # [NEW] 即使在 Yellow Zone，已知异常的个股也需要先行清理其脏数据
            if abnormal_list:
                purge_codes = [item['code'] for item in abnormal_list]
                await service.purge_tick_data(trade_date, purge_codes)

        else:
            logger.info(f"🔴 Zone 3 (Red): 数据大面积缺失，启动 Failover 集中修复模式")
            action_recommendation = "FAILOVER"
            failover_mode = True
            
            # [NEW] Failover 模式下，立即清理所有异常股，准备补采
            if abnormal_list:
                purge_codes = [item['code'] for item in abnormal_list]
                await service.purge_tick_data(trade_date, purge_codes)
            
            # Failover 模式下，全量修复
            extra_codes = [item['code'] for item in abnormal_list]
            missing_list.extend(extra_codes)

        # 5. 输出规范 JSON
        result = {
            "date": trade_date,
            "metrics": {
                "total_expected": expected_count,
                "total_actual": len(actual_data),
                "missing_count": missing_count,
                "abnormal_count": abnormal_count,
                "missing_rate": missing_rate,
                "abnormal_rate": abnormal_rate
            },
            "diagnosis": {
                "action": action_recommendation,
                "failover_mode": failover_mode
            },
            "missing_list": missing_list,
            "abnormal_list": abnormal_list,
            "status": "FAIL" if (missing_rate > 0.01 or abnormal_count > 100) else "SUCCESS"
        }
        
        print(f"GSD_OUTPUT_JSON: {json.dumps(result)}")

    except Exception as e:
        logger.error(f"❌ 深度审计 Job 运行异常: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(main())
