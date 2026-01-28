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

        logger.info(f"�️ 开始深度审计: {trade_date}")

        # 1. 加载预期名单 (Inventory)
        # 获取全市场 A 股名单 (排除北交所逻辑已内置在 StockUniverse)
        expected_codes = await service.stock_universe.get_all_a_stocks()
        expected_count = len(expected_codes)
        logger.info(f"📋 预期 A 股总数: {expected_count}")

        if expected_count == 0:
            logger.error("❌ 无法获取预期股票名单，审计无法进行")
            sys.exit(1)

        # 2. 查询 ClickHouse 实际数据 - 深度连续性校验
        # 对接 PostMarketGateService._check_all_ticks_continuity 逻辑
        std = TickStandards.IntradayPostMarket
        min_active = std.MIN_ACTIVE_MINUTES
        min_time = std.MIN_TIME
        max_time = std.MAX_TIME
        
        query = f"""
        SELECT 
            stock_code,
            first_tick,
            last_tick,
            active_minutes,
            tick_count
        FROM (
            SELECT 
                stock_code,
                min(tick_time) as first_tick,
                max(tick_time) as last_tick,
                countDistinct(substring(tick_time, 1, 5)) as active_minutes,
                count() as tick_count
            FROM stock_data.tick_data_intraday 
            WHERE trade_date = '{trade_date.replace('-', '')}'
            GROUP BY stock_code
        )
        """
        
        async with service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query)
                rows = await cursor.fetchall()
        
        # 3. 分析指标
        actual_data = {row[0]: row for row in rows}
        logger.info(f"📉 实际入库股票数: {len(actual_data)}")

        missing_list = []
        abnormal_list = []
        
        # 遍历预期名单，检查完整性
        for code in expected_codes:
            if code not in actual_data:
                missing_list.append(code)
                continue
            
            # 连续性校验
            # row: [stock_code, first_tick, last_tick, active_minutes, tick_count]
            _, first_t, last_t, active_m, count = actual_data[code]
            
            # 标准化时间用于比较
            f_cmp = first_t if len(first_t) == 8 else f"{first_t}:00"
            l_cmp = last_t if len(last_t) == 8 else f"{last_t}:00"
            
            is_abnormal = False
            reasons = []
            
            if active_m < min_active:
                is_abnormal = True
                reasons.append(f"时长不足({active_m}/{min_active})")
            
            if f_cmp > min_time:
                is_abnormal = True
                reasons.append(f"开盘晚({first_t})")
                
            if l_cmp < max_time:
                is_abnormal = True
                reasons.append(f"收盘早({last_t})")
            
            # 基础行数辅助检查 (args.threshold)
            if count < args.threshold:
                # 如果还没被判定为 abnormal，补一个理由
                if not is_abnormal:
                    is_abnormal = True
                    reasons.append(f"行数少({count})")

            if is_abnormal:
                abnormal_list.append({
                    "code": code,
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

        logger.info(f"🚦 审计摘要: 缺失={missing_count}({missing_rate:.2%}), 异常={abnormal_count}({abnormal_rate:.2%})")

        # 对接 Node-58 韧性策略
        if missing_rate < 0.01 and abnormal_count < 50:
            # Zone 1: Green (< 1%) -> 几乎完美，忽略或微小修复
            logger.info("🟢 Zone 1 (Green): 质量极佳，无需特殊干预")
            action_recommendation = "NONE"
            
        elif missing_rate < 0.10:
            # Zone 2: Yellow (< 10%) -> 局部抖动，触发 AI 核查并精准补采
            logger.info("🟡 Zone 2 (Yellow): 局部数据异常，启用 AI 审计门禁")
            action_recommendation = "AI_AUDIT"
            
        else:
            # Zone 3: Red (>= 10%) -> 系统性缺失，触发集群代偿 (Failover)
            logger.info("🔴 Zone 3 (Red): 集群级数据塌方，启动补偿补采模式")
            action_recommendation = "FAILOVER"
            failover_mode = True

        # 5. 输出结果 (StdOut)
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
                "failover_mode": failover_mode,
                "standards": {
                    "min_active_minutes": min_active,
                    "min_time": min_time,
                    "max_time": max_time
                }
            },
            "missing_list": missing_list,
            "abnormal_list": abnormal_list,
            "status": "FAIL" if (missing_rate > 0.01 or abnormal_count > 100) else "SUCCESS"
        }
        
        print(f"GSD_OUTPUT_JSON: {json.dumps(result)}")

    except Exception as e:
        logger.error(f"❌ 审计失败: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await service.close()

if __name__ == "__main__":
    asyncio.run(main())
