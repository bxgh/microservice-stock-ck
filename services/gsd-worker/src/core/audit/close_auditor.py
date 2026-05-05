import logging
from typing import List, Optional, Set, Dict, Any
from .base import BaseAuditor

logger = logging.getLogger("CloseAuditor")

class CloseAuditor(BaseAuditor):
    """盘后数据审计器 (KLine vs Tick)"""
    
    async def run(self):
        target_scope = await self.get_target_scope()
        if not target_scope:
            return {"action": "NONE", "reason": "empty_scope"}

        from datetime import datetime
        import pytz
        CST = pytz.timezone('Asia/Shanghai')
        today_str = datetime.now(CST).strftime("%Y-%m-%d")
        is_today = (self.target_date == today_str)

        benchmark_map = {}
        benchmark_type = "KLINE"

        # 1. 策略选择: 如果是当天，优先尝试拉取 15:00 快照
        if is_today:
            logger.info(f"📅 检测到当天审计 ({self.target_date})，优先拉取收盘快照...")
            async with self.service.clickhouse_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"""
                        SELECT stock_code, argMax(total_volume, snapshot_time) as snap_vol, argMax(current_price, snapshot_time) as snap_price
                        FROM snapshot_data_distributed 
                        WHERE trade_date = '{self.target_date}'
                          AND snapshot_time >= '{self.target_date} 14:59:00'
                          AND snapshot_time <= '{self.target_date} 15:05:00'
                        GROUP BY stock_code
                    """)
                    rows = await cursor.fetchall()
                    if rows:
                        benchmark_map = {r[0]: {'vol': float(r[1]) * 100, 'close': float(r[2])} for r in rows}
                        benchmark_type = "SNAPSHOT"
                        logger.info(f"✅ 使用 {len(benchmark_map)} 条收盘快照作为基准数据")

        # 2. 回退/降级逻辑: 如果快照缺失或非当天，使用 K 线
        if not benchmark_map:
            if is_today:
                logger.warning("⚠️ 当天收盘快照缺失，降级使用 K 线数据...")
            
            # K线就绪检查
            if not await self._check_kline_ready(target_scope):
                logger.error("❌ K线数据未就绪! (Threshold 100%)")
                return {"action": "NONE", "status": "failed", "reason": "kline_not_ready"}
            
            async with self.service.clickhouse_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(f"""
                        SELECT stock_code, volume, amount, close_price
                        FROM stock_data.stock_kline_daily
                        WHERE trade_date = '{self.target_date}'
                    """)
                    rows = await cursor.fetchall()
                    benchmark_map = {self._normalize_code(r[0]): {'vol': float(r[1]), 'close': float(r[3]), 'amt': float(r[2])} for r in rows}
                    benchmark_type = "KLINE"
            logger.info(f"✅ 使用 {len(benchmark_map)} 条 K 线数据作为基准数据")

        # 3. 获取待审计的分笔聚合数据
        tick_map = {}
        target_table = "tick_data_intraday" if is_today else "tick_data"
        async with self.service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"""
                    SELECT stock_code, count(), sum(volume), sum(amount), argMax(price, tick_time)
                    FROM {target_table}
                    WHERE trade_date = '{self.target_date}'
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

        # 4. 执行对账
        missing_list = []
        invalid_list = []
        valid_cnt = 0
        
        for code in target_scope:
            if code not in tick_map:
                missing_list.append(code)
                continue
            
            if code not in benchmark_map:
                continue
                
            t_data = tick_map[code]
            b_data = benchmark_map[code]
            
            # 价格检查 (0.01 容差)
            if abs(t_data['price'] - b_data['close']) > 0.01:
                invalid_list.append({
                    'code': code, 
                    'reason': f"price_mismatch ({benchmark_type})",
                    'amt_diff': abs(t_data['vol'] - b_data['vol']) * t_data['price'] # 估算差异额
                })
                continue
                
            # 量额 2% 阈值检查
            vol_diff_pct = abs(t_data['vol'] - b_data['vol']) / b_data['vol'] if b_data['vol'] > 0 else 0
            
            # 如果基准是 K 线，可以用金额检查；如果是快照，主要参考量
            mismatch = False
            if benchmark_type == "KLINE":
                amt_diff_pct = abs(t_data['amt'] - b_data['amt']) / b_data['amt'] if b_data['amt'] > 0 else 0
                if vol_diff_pct > 0.02 or amt_diff_pct > 0.02:
                    mismatch = True
            else:
                if vol_diff_pct > 0.02:
                    mismatch = True

            if mismatch:
                invalid_list.append({
                    'code': code,
                    'reason': f"data_mismatch ({benchmark_type})",
                    'amt_diff': abs(t_data['vol'] - b_data['vol']) * t_data['price']
                })
                continue
            
            valid_cnt += 1

        # 5. 诊断与输出
        heavy_faults = [item['code'] for item in invalid_list if item['amt_diff'] >= 100000]
        light_faults = [item['code'] for item in invalid_list if item['amt_diff'] < 100000]
        
        total_faults = len(missing_list) + len(invalid_list)
        threshold = self.threshold or 200
        
        if total_faults == 0:
            action = "NONE"
        elif total_faults > threshold:
            action = "FAILOVER"
        else:
            action = "AI_AUDIT"
            
        output = {
            "target_date": self.target_date,
            "benchmark": benchmark_type,
            "stats": {
                "valid": valid_cnt,
                "missing": len(missing_list),
                "heavy_fault": len(heavy_faults),
                "light_fault": len(light_faults)
            },
            "missing_list": list(set(missing_list + heavy_faults)),
            "abnormal_list": light_faults,
            "diagnosis": {
                "action": action,
                "failover_mode": "DEFAULT"
            }
        }
        return output

    async def _check_kline_ready(self, target_scope: Set[str]) -> bool:
        expected_count = len(target_scope)
        async with self.service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"""
                    SELECT count() FROM stock_data.stock_kline_daily 
                    WHERE trade_date = '{self.target_date}'
                    AND stock_code NOT LIKE 'bj.%' AND stock_code NOT LIKE '%.BJ'
                """)
                actual_count = (await cursor.fetchone())[0]
        return actual_count / expected_count >= 1.0
