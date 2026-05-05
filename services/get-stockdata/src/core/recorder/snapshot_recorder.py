import asyncio
import logging
import time
import os
import signal
from datetime import datetime
from typing import List

# Standardized imports with src. prefix
from src.core.stock_pool.manager import StockPoolManager, PoolLevel
from src.core.storage.parquet_writer import ParquetWriter
from src.storage.clickhouse_writer import ClickHouseWriter
from src.core.storage.dual_writer import DualWriter
from src.core.scheduling.scheduler import AcquisitionScheduler
from src.data_access.redis_pool import RedisPoolManager
from mootdx.quotes import Quotes
import json

# --- Monkeypatch: Force mootdx to use pytdx for connection ---
try:
    import tdxpy.hq
    import pytdx.hq
    print("⚡ Monkeypatching: Overwriting tdxpy.hq.TdxHq_API with pytdx.hq.TdxHq_API")
    tdxpy.hq.TdxHq_API = pytdx.hq.TdxHq_API
except Exception as e:
    print(f"Monkeypatch failed: {e}")
# -------------------------------------------------------------

class SnapshotRecorder:
    """
    快照录制器 (Refactored for Code Quality)
    负责对L1池进行高频录制，并双写到 Parquet 和 ClickHouse
    """
    
    def __init__(self, pool_manager=None, storage_path: str = None):
        self.logger = logging.getLogger("SnapshotRecorder")
        self.pool_manager = pool_manager or StockPoolManager()
        self.scheduler = AcquisitionScheduler()
        self.is_running = False
        self.client = None
        self.redis = None
        
        # 初始化存储路径
        if storage_path is None:
            storage_path = os.getenv('SNAPSHOT_STORAGE_PATH', '/app/data/snapshots')
            
        # 初始化双写存储
        parquet_writer = ParquetWriter(storage_path)
        
        # 从环境变量获取 ClickHouse 配置
        clickhouse_host = os.getenv('CLICKHOUSE_HOST', 'microservice-stock-clickhouse')
        clickhouse_port = int(os.getenv('CLICKHOUSE_PORT', 9000))
        clickhouse_db = os.getenv('CLICKHOUSE_DB', 'stock_data')
        
        clickhouse_writer = ClickHouseWriter(
            host=clickhouse_host,
            port=clickhouse_port,
            database=clickhouse_db,
            table_name=os.getenv('CLICKHOUSE_SNAPSHOT_TABLE', 'snapshot_data_distribute')
        )
        
        self.writer = DualWriter(parquet_writer, clickhouse_writer)
        self.logger.info(f"📦 Storage initialized: Parquet({storage_path}) + ClickHouse({clickhouse_host}:{clickhouse_port})")
        
    async def _connect(self):
        """连接数据源"""
        try:
            # 1. 尝试使用默认配置 (由 entrypoint.sh 的 bestip 生成)
            self.logger.info("🔍 Attempting Mootdx connection using default config...")
            loop = asyncio.get_event_loop()
            self.client = await loop.run_in_executor(
                None, 
                lambda: Quotes.factory(market='std', bestip=False, timeout=5)
            )
            # 测试连接
            self.client.quotes(symbol="000001")
            self.logger.info("✅ Connected to Mootdx via Default Config")
            return
        except Exception as e:
            self.logger.warning(f"⚠️ Default config connection failed ({e}), trying bestip discovery...")
        
        try:
            # 2. 尝试自动搜索最佳服务器 (带超时)
            loop = asyncio.get_event_loop()
            self.client = await loop.run_in_executor(
                None, 
                lambda: Quotes.factory(market='std', bestip=True, timeout=10)
            )
            self.logger.info("✅ Connected to Mootdx via BestIP Discovery")
        except Exception as e:
            self.logger.warning(f"⚠️ BestIP Discovery failed ({e}), trying fallback servers...")
            
            # 3. 备用列表 (直接指定 host/port)
            fallbacks = [
                ("119.147.212.81", 7709),
                ("114.80.149.19", 7709),
                ("114.80.149.22", 7709)
            ]
            
            for ip, port in fallbacks:
                try:
                    self.logger.info(f"🔗 Testing fallback server: {ip}:{port}")
                    self.client = Quotes.factory(market='std', host=ip, port=port, timeout=5)
                    self.logger.info(f"✅ Connected to fallback server: {ip}")
                    return
                except Exception as ex:
                    self.logger.debug(f"Fallback {ip} failed: {ex}")
            
            raise ConnectionError("All TDX servers are unreachable")

    def stop(self):
        """停止录制"""
        self.logger.info("🛑 Stopping Snapshot Recorder...")
        self.is_running = False

    async def start(self):
        """启动录制"""
        self.logger.info("🚀 Starting Snapshot Recorder...")
        self.is_running = True
        
        # 初始化连接
        try:
            await self._connect()
        except ConnectionError as e:
            self.logger.error(f"❌ Failed to connect to Mootdx: {e}")
            return
        except Exception as e:
            self.logger.error(f"❌ An unexpected error occurred during connection: {e}")
            return

        # 获取L1池 (动态加载)
        l1_symbols = self.pool_manager.get_pool_symbols(PoolLevel.L1_CORE)
        if not l1_symbols:
            self.logger.warning("⚠️ L1 Pool is empty! Please check your config.")
            return

        self.logger.info(f"🎯 Target: {len(l1_symbols)} stocks in L1 Pool")
        
        # 分批处理 (每批80个)
        batch_size = 80
        batches = [l1_symbols[i:i + batch_size] for i in range(0, len(l1_symbols), batch_size)]
        
        round_count = 0
        
        while self.is_running:
            try:
                # 1. 智能调度检查
                if not self.scheduler.should_run_now():
                    self.logger.info("⏸️ Not in trading hours. Waiting...")
                    await self.scheduler.wait_for_next_run()
                    # 重新尝试连接
                    if not self.client:
                        await self._connect()
                    # 重新初始化 Redis
                    if not self.redis:
                        self.redis = await RedisPoolManager.get_instance().get_redis()
                    continue

                if not self.redis:
                    self.redis = await RedisPoolManager.get_instance().get_redis()

                round_start = time.time()
                round_count += 1
                round_timestamp = datetime.now()
                
                self.logger.debug(f"Round {round_count} Start at {round_timestamp.strftime('%H:%M:%S')}...")
                
                total_snapshots = 0
                all_snapshots = []
                
                for batch in batches:
                    if not self.is_running: break
                    try:
                        clean_batch = [str(s) for s in batch]
                        df = self.client.quotes(symbol=clean_batch)
                        if df is not None and not df.empty:
                            total_snapshots += len(df)
                            all_snapshots.append(df)
                    except Exception as e:
                        self.logger.error(f"  ❌ Batch failed: {e}")
                    
                    await asyncio.sleep(0.05) # 降低批次间延迟提高采集密度
                
                # 双写存储
                if all_snapshots and self.is_running:
                    import pandas as pd
                    combined_df = pd.concat(all_snapshots, ignore_index=True)
                    p_success, c_success = await self.writer.write(combined_df, round_timestamp)
                    
                    if not (p_success and c_success):
                        self.logger.warning(f"  ⚠️ Write status: Parquet={'OK' if p_success else 'FAIL'}, CK={'OK' if c_success else 'FAIL'}")
                    
                    # 3. 触发增量分笔采集任务
                    await self._emit_tick_tasks(combined_df)
                
                duration = time.time() - round_start
                self.logger.info(f"✅ Round {round_count} Complete: {total_snapshots} snapshots in {duration:.2f}s")
                
                # 至少保持3秒间隔
                if duration < 3:
                    await asyncio.sleep(3 - duration)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"⚠️ Error in recording loop: {e}")
                await asyncio.sleep(5)
                
        self.logger.info("🛑 Recorder cleaning up...")
        try:
            self.writer.close()
        except:
            pass

    async def _emit_tick_tasks(self, df):
        """
        根据成交量变化触发分笔采集任务 (Refactored to Redis Stream)
        """
        if df is None or df.empty or self.redis is None:
            return

        try:
            # 获取所有股票的当前总成交量
            # Mootdx 'vol' is total volume in lots (usually), 'amount' is total amount
            current_data = {str(row.code): int(getattr(row, 'vol', 0)) for row in df.itertuples(index=False)}
            stock_codes = list(current_data.keys())
            
            # 批量获取 Redis 中的上次成交量
            today_str = datetime.now().strftime('%Y%m%d')
            vol_cache_key = f"snapshot:vol:{today_str}"
            
            last_volumes = await self.redis.hmget(vol_cache_key, stock_codes)
            
            # Redis Stream Key
            STREAM_KEY_JOBS = "stream:tick:jobs"
            
            updates_to_cache = {}
            pushed_count = 0
            
            import uuid
            
            for i, code in enumerate(stock_codes):
                current_vol = current_data[code]
                last_vol = int(last_volumes[i]) if last_volumes[i] is not None else 0
                
                # 触发条件: 成交量增加 OR (首次出现且有量)
                if current_vol > last_vol or (last_vol == 0 and current_vol > 0):
                    # 构造 TickJob 消息 (符合 gsd_shared.redis_protocol.TickJob)
                    # 使用 raw dict 避免依赖导入问题
                    job_payload = {
                        "job_id": str(uuid.uuid4()),
                        "stock_code": code,
                        "type": "intraday",  # JobType.INTRADAY
                        "date": today_str,
                        "market": "", # Optional
                        "last_vol": str(last_vol),
                        "retry_count": "0"
                    }
                    
                    # 发布到 Redis Stream
                    await self.redis.xadd(STREAM_KEY_JOBS, job_payload)
                    
                    updates_to_cache[code] = current_vol
                    pushed_count += 1
                    
            # 批量更新 Redis 缓存
            if updates_to_cache:
                await self.redis.hset(vol_cache_key, mapping=updates_to_cache)
                await self.redis.expire(vol_cache_key, 86400)
                
            if pushed_count > 0:
                self.logger.debug(f"📤 Published {pushed_count} tick jobs to Stream")

        except Exception as e:
            self.logger.error(f"Error emitting tick tasks: {e}")


def handle_signals(recorder):
    """设置信号处理"""
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, recorder.stop)

if __name__ == "__main__":
    # 配置基础日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 模拟管理对象
    manager = StockPoolManager()
    
    # 从环境变量或默认路径启动
    storage_path = os.getenv('SNAPSHOT_STORAGE_PATH', '/app/data/snapshots')
    recorder = SnapshotRecorder(manager, storage_path=storage_path)
    
    # 注册信号处理
    try:
        handle_signals(recorder)
    except NotImplementedError:
        # Windows 不支持 add_signal_handler
        pass
    
    try:
        asyncio.run(recorder.start())
    except Exception as e:
        print(f"Runtime error: {e}")
        import traceback
        traceback.print_exc()
