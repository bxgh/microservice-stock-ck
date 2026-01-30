
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
from datetime import datetime, timedelta
import pytz
import asynch

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
    def __init__(self):
        self.service = TickSyncService()
        self.target_date = datetime.now(CST).strftime("%Y-%m-%d")
        
    async def initialize(self):
        await self.service.initialize()
        
    async def close(self):
        await self.service.close()

    async def get_target_scope(self) -> set:
        """Step 1: 确定目标范围 (Exclude BJ)"""
        # 1. 从 Redis 获取 sync_list (全量)
        # Assuming key is 'monitor:stock_list' or similar managed by Orchestrator
        # But TickSyncService usually uses a specific key. Let's use service.fetch_sync_list which encapsulates logic.
        # But we need EXPLICIT exclusion of BJ.
        
        all_codes = await self.service.fetch_sync_list(scope="all")
        if not all_codes:
            # Fallback for dev: try to get from redis raw key if needed or list_stock_kline table
            logger.warning("fetch_sync_list returned empty. (Redis empty?)")
            return set()

        # 2. Filter BJ
        target_scope = set()
        for code in all_codes:
            # Code validation: 
            # BJ exchanges: 8xxxxx, 4xxxxx, 92xxxx
            # Or prefix 'bj.'
            # Tick codes usually don't have prefix here? Let's assume standardized 6 digits.
            if code.startswith(('8', '4', '92')):
                continue
            if code.startswith('bj'):
                continue
            target_scope.add(code)
            
        logger.info(f"🎯 目标范围: 总数={len(all_codes)} -> 过滤北证后={len(target_scope)}")
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
                await cursor.execute(f"""
                    SELECT count() 
                    FROM stock_data.stock_kline_daily 
                    WHERE trade_date = '{self.target_date}'
                    AND stock_code NOT LIKE 'bj.%' 
                    AND stock_code NOT LIKE '%.BJ'
                    AND stock_code NOT LIKE 'sh.8%%'
                    AND stock_code NOT LIKE 'sz.8%%'
                """)
                row = await cursor.fetchone()
                actual_count = row[0] if row else 0

        coverage = actual_count / expected_count
        logger.info(f"🏗️  K线就绪检查: 实际={actual_count}/预期={expected_count} (覆盖率={coverage:.2%})")

        if coverage < 0.99:
            logger.error(f"❌ K线数据未就绪! (Threshold 99%)")
            # For strict mode, we might want to return False, but let's see actual counts first.
            if coverage == 0:
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
        """Step 3: 高速内存对账"""
        logger.info("🚀 开始高速内存对账...")
        
        # 1. Load Ticks (Batch)
        # Map: code -> (count, vol, last_price)
        tick_map = {}
        async with self.service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                logger.info("   -> Loading Tick Data...")
                await cursor.execute(f"""
                    SELECT stock_code, count(), sum(volume), argMax(price, tick_time)
                    FROM tick_data_intraday
                    WHERE trade_date = '{self.target_date}'
                    GROUP BY stock_code
                """)
                # Use asynch iteration to handle large result set
                rows = await cursor.fetchall()
                for r in rows:
                    tick_map[r[0]] = {'count': r[1], 'vol': float(r[2]), 'price': float(r[3])}
        
        logger.info(f"   -> Loaded {len(tick_map)} tick records.")

        # 2. Load KLines (Batch)
        # Map: code (stripped) -> (vol, close)
        kline_map = {}
        async with self.service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                logger.info("   -> Loading KLine Data...")
                # Note: KLine codes have 'sh.'/ 'sz.' prefix usually
                await cursor.execute(f"""
                    SELECT stock_code, volume, close_price
                    FROM stock_data.stock_kline_daily
                    WHERE trade_date = '{self.target_date}'
                """)
                rows = await cursor.fetchall()
                for r in rows:
                    # Strip prefix/suffix
                    std_code = self._normalize_code(r[0])
                    kline_map[std_code] = {'vol': float(r[1]), 'close': float(r[2])}
        
        logger.info(f"   -> Loaded {len(kline_map)} kline records.")

        # 3. Vectorized Compare
        missing_list = []
        invalid_list = []
        valid_cnt = 0
        
        for code in target_scope:
            # L1 Existence
            if code not in tick_map:
                missing_list.append(code)
                continue
            
            # L2 Accuracy
            if code not in kline_map:
                # KLine missing for this specific code (even if total coverage is high)
                # Treat as Invalid or Skip? 
                # According to "Check & Wait", if global coverage is high, this might be a suspension.
                # Just skip or warning.
                continue
                
            t_data = tick_map[code]
            k_data = kline_map[code]
            
            # Check Price (0.01)
            price_diff = abs(t_data['price'] - k_data['close'])
            if price_diff > 0.01:
                invalid_list.append({
                    'code': code, 
                    'reason': f"Price Diff {price_diff:.3f} (Tick={t_data['price']}, K={k_data['close']})"
                })
                continue
                
            # Check Volume (2%)
            if k_data['vol'] > 0:
                vol_diff_pct = abs(t_data['vol'] - k_data['vol']) / k_data['vol']
                if vol_diff_pct > 0.02:
                    invalid_list.append({
                        'code': code,
                        'reason': f"Vol Diff {vol_diff_pct:.2%} (Tick={t_data['vol']}, K={k_data['vol']})"
                    })
                    continue
            
            valid_cnt += 1

        # 4. Report
        logger.info(f"\n{'='*40}")
        logger.info(f"📊 审计报告 ({self.target_date})")
        logger.info(f"   ✅ Valid:   {valid_cnt}")
        logger.info(f"   ⭕ Missing: {len(missing_list)}")
        logger.info(f"   ❌ Invalid: {len(invalid_list)}")
        logger.info(f"{'='*40}\n")
        
        # Output details for Invalid
        if invalid_list:
            logger.info("Sample Invalid:")
            for item in invalid_list[:5]:
                logger.info(f"   - {item['code']}: {item['reason']}")

        return missing_list, invalid_list

    async def purge_invalid_data(self, invalid_list: list):
        """Step 4: 物理清洗 (DELETE Invalid)"""
        if not invalid_list:
            return
            
        codes = [item['code'] for item in invalid_list]
        logger.info(f"🧹 执行物理清洗: 对象数={len(codes)}")
        
        # Split into batches to avoid SQL too long
        batch_size = 1000
        for i in range(0, len(codes), batch_size):
            batch = codes[i:i+batch_size]
            code_str = ",".join([f"'{c}'" for c in batch])
            
            # Must delete from LOCAL table. Assuming simple Distributed->Local mapping.
            # In production, we should find the local table name dynamically or from config.
            # Here we hardcode to tick_data_intraday_local based on introspection.
            sql = f"""
                ALTER TABLE tick_data_intraday_local ON CLUSTER default
                DELETE WHERE trade_date = '{self.target_date}' 
                AND stock_code IN ({code_str})
            """
            
            try:
                # Use execute (DDL)
                async with self.service.clickhouse_pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(sql)
                logger.info(f"   -> Batch {i//batch_size + 1}: Deleter Triggered for {len(batch)} records.")
            except Exception as e:
                logger.error(f"   -> Batch {i//batch_size + 1} Failed: {e}")
                
        # Wait for mutations to finish? 
        # ClickHouse mutations are async. We don't block here, just assume it will happen.

    async def trigger_repair(self, repair_codes: list):
        """Step 5: 触发补采"""
        if not repair_codes:
            logger.info("✅ 无需补采。")
            return
            
        logger.info(f"🔧 触发补采任务: 数量={len(repair_codes)}")
        
        # Use sync_stocks method
        # Deep inspection result: MootdxFetcher expects 6-digit codes (e.g. '600000')
        # Do NOT add prefixes manually.
        
        try:
            # We call sync_stocks. 
            # Note: sync_stocks signature is (stock_codes, trade_date, concurrency, force)
            await self.service.sync_stocks(
                stock_codes=repair_codes,
                trade_date=self.target_date, 
                concurrency=20, # Higher concurrency for repair
                force=True
            )
            logger.info("✨ 补采任务提交完成")
            
        except Exception as e:
            logger.error(f"❌ 补采任务执行失败: {e}")

    async def run(self):
        try:
            await self.initialize()
            
            # Step 1
            target_scope = await self.get_target_scope()
            if not target_scope:
                logger.error("Empty target scope. Exit.")
                return
                
            # Step 2
            is_ready = await self.check_dependency(target_scope)
            if not is_ready:
                logger.error("Dependency Check Failed. ABORTING VALIDATION (NO DEGRADE).")
                sys.exit(1) 
                
            # Step 3
            missing, invalid = await self.execute_validation(target_scope)
            
            # Step 4: Actions (Purge & Repair)
            # 4.1 Purge Invalid
            if invalid:
                await self.purge_invalid_data(invalid)
                
            # 4.2 Repair (Missing + Invalid)
            # Combine unique codes
            invalid_codes = [item['code'] for item in invalid]
            repair_set = set(missing + invalid_codes)
            
            if repair_set:
                await self.trigger_repair(list(repair_set))
            
        finally:
            await self.close()

if __name__ == "__main__":
    job = AuditJob()
    asyncio.run(job.run())
