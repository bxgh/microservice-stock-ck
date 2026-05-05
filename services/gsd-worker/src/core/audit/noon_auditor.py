import logging
from typing import List, Optional, Set, Dict, Any
from .base import BaseAuditor

logger = logging.getLogger("NoonAuditor")

class NoonAuditor(BaseAuditor):
    """午间高精度审计器 (Snapshot vs Tick)"""
    
    async def run(self):
        target_scope = await self.get_target_scope()
        if not target_scope:
            return {"action": "NONE", "reason": "empty_scope"}

        logger.info(f"🚀 开始午间高精度对账 (Target: {self.target_date})...")
        
        # 1. 获取 11:30 快照
        snap_map = {}
        async with self.service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"""
                    SELECT stock_code, argMax(total_volume, snapshot_time) as snap_vol
                    FROM snapshot_data_distributed 
                    WHERE trade_date = '{self.target_date}'
                      AND snapshot_time >= '{self.target_date} 11:29:00'
                      AND snapshot_time <= '{self.target_date} 11:30:05'
                    GROUP BY stock_code
                """)
                rows = await cursor.fetchall()
                snap_map = {r[0]: float(r[1]) * 100 for r in rows}
        
        if not snap_map:
            logger.warning("⚠️ Snapshot table empty for today. Skipping noon validation.")
            return {"action": "NONE", "reason": "no_snapshots"}

        # 2. 获取分笔数据聚合
        tick_map = {}
        async with self.service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"""
                    SELECT stock_code, sum(volume) as tick_sum
                    FROM tick_data_intraday
                    WHERE trade_date = '{self.target_date}'
                      AND tick_time <= '11:30:00'
                    GROUP BY stock_code
                """)
                rows = await cursor.fetchall()
                tick_map = {r[0]: float(r[1]) for r in rows}

        # 3. 对账
        invalid_list = []
        valid_cnt = 0
        
        for code in target_scope:
            if code not in snap_map: continue
            
            s_vol = snap_map[code]
            t_vol = tick_map.get(code, 0)
            
            if s_vol <= 0: continue
            
            diff_abs = abs(t_vol - s_vol)
            diff_pct = diff_abs / s_vol
            if diff_pct > 0.01 and diff_abs > 100000: # 1% 阈值且绝对值 > 10万股
                invalid_list.append({
                    'code': code,
                    'reason': f"Noon Vol Mismatch ({diff_pct:.1%}, diff={int(diff_abs)})",
                    'amt_diff': diff_abs
                })
                continue
            
            valid_cnt += 1

        logger.info(f"📊 午间审计结果: Valid={valid_cnt}, Invalid={len(invalid_list)}")
        
        # 4. 诊断与输出
        invalid_count = len(invalid_list)
        threshold = self.threshold or 200
        if invalid_count == 0:
            action = "NONE"
        elif invalid_count > threshold:
            action = "FAILOVER"
        else:
            action = "AI_AUDIT"
            
        output = {
            "target_date": self.target_date,
            "stats": {
                "valid": valid_cnt,
                "missing": 0,
                "heavy_fault": invalid_count,
                "light_fault": 0
            },
            "missing_list": [item['code'] for item in invalid_list], # 午间直接修复
            "abnormal_list": [],
            "diagnosis": {
                "action": action,
                "failover_mode": "DEFAULT"
            }
        }
        return output
