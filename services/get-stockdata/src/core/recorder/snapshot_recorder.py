import asyncio
import time
import os
from datetime import datetime
from typing import List
from src.core.stock_pool.manager import StockPoolManager, PoolLevel
from src.core.storage.parquet_writer import ParquetWriter
from src.storage.clickhouse_writer import ClickHouseWriter
from src.core.storage.dual_writer import DualWriter
from src.core.scheduling.scheduler import AcquisitionScheduler
from mootdx.quotes import Quotes

class SnapshotRecorder:
    """
    快照录制器
    负责对L1池进行高频录制，并双写到 Parquet 和 ClickHouse
    """
    
    def __init__(self, pool_manager: StockPoolManager, storage_path: str = "/app/data/snapshots"):
        self.pool_manager = pool_manager
        self.scheduler = AcquisitionScheduler()
        self.is_running = False
        self.client = None
        
        # 初始化双写存储
        parquet_writer = ParquetWriter(storage_path)
        
        # 从环境变量获取 ClickHouse 配置
        clickhouse_host = os.getenv('CLICKHOUSE_HOST', 'microservice-stock-clickhouse')
        clickhouse_port = int(os.getenv('CLICKHOUSE_PORT', 9000))
        clickhouse_db = os.getenv('CLICKHOUSE_DB', 'stock_data')
        
        clickhouse_writer = ClickHouseWriter(
            host=clickhouse_host,
            port=clickhouse_port,
            database=clickhouse_db
        )
        
        self.writer = DualWriter(parquet_writer, clickhouse_writer)
        print(f"📦 Storage initialized: Parquet({storage_path}) + ClickHouse({clickhouse_host}:{clickhouse_port})")
        
    async def start(self):
        """启动录制"""
        print("🚀 Starting Snapshot Recorder...")
        self.is_running = True
        
        # 初始化连接
        try:
            # 尝试不使用heartbeat，或者单线程，看看是否稳定
            # 禁用heartbeat和multithread以避免asyncio错误
            self.client = Quotes.factory(market='std', multithread=False, heartbeat=False)
            print("✅ Connected to Mootdx")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return

        # 获取L1池
        l1_symbols = self.pool_manager.get_pool_symbols(PoolLevel.L1_CORE)
        if not l1_symbols:
            print("⚠️ L1 Pool is empty. Initializing...")
            self.pool_manager.initialize_static_l1_pool()
            l1_symbols = self.pool_manager.get_pool_symbols(PoolLevel.L1_CORE)
        
        print(f"🎯 Target: {len(l1_symbols)} stocks in L1 Pool")
        
        # 分批处理 (每批80个)
        batch_size = 80
        batches = [l1_symbols[i:i + batch_size] for i in range(0, len(l1_symbols), batch_size)]
        
        round_count = 0
        
        while self.is_running:
            # 1. 智能调度检查
            if not self.scheduler.should_run_now():
                print("⏸️ Not in trading hours. Waiting...")
                await self.scheduler.wait_for_next_run()
                # 唤醒后重新检查连接
                if not self.client:
                    self.client = Quotes.factory(market='std', multithread=False, heartbeat=False)
                continue

            round_start = time.time()
            round_count += 1
            
            round_timestamp = datetime.now()
            print(f"\n⏱️ Round {round_count} Start at {round_timestamp.strftime('%H:%M:%S')}...")
            
            total_snapshots = 0
            all_snapshots = []  # 收集本轮所有快照
            
            for batch in batches:
                try:
                    # 简单清洗代码，确保是字符串
                    clean_batch = [str(s) for s in batch]
                    
                    # 获取快照
                    # 注意：mootdx的quotes方法在某些版本中可能不是异步的，或者内部使用了asyncio
                    # 如果是同步方法，直接调用
                    # 如果是异步方法，需要await
                    # 根据源码，quotes是同步方法
                    df = self.client.quotes(symbol=clean_batch)
                    
                    if df is not None and not df.empty:
                        count = len(df)
                        total_snapshots += count
                        all_snapshots.append(df)  # 收集快照
                        
                except Exception as e:
                    print(f"  ❌ Batch failed: {e}")
                
                # 批次间微小延时，防止瞬时QPS过高
                await asyncio.sleep(0.1)
            
            # 保存本轮所有快照 (双写)
            if all_snapshots:
                import pandas as pd
                combined_df = pd.concat(all_snapshots, ignore_index=True)
                
                # 使用 DualWriter 异步写入
                p_success, c_success = await self.writer.write(combined_df, round_timestamp)
                
                status_icon = "✅" if (p_success and c_success) else "⚠️"
                print(f"  {status_icon} Saved: Parquet={'OK' if p_success else 'FAIL'}, ClickHouse={'OK' if c_success else 'FAIL'}")
            
            duration = time.time() - round_start
            print(f"✅ Round {round_count} Complete: {total_snapshots} snapshots in {duration:.2f}s")
            
            # 控制频率：确保每轮至少3秒
            if duration < 3:
                wait = 3 - duration
                print(f"  Waiting {wait:.2f}s...")
                await asyncio.sleep(wait)
                
        print("🛑 Recorder Stopped")
        
        # 关闭连接
        try:
            self.writer.close()
        except:
            pass

if __name__ == "__main__":
    # 测试运行
    manager = StockPoolManager()
    recorder = SnapshotRecorder(manager, storage_path="/tmp/snapshots")  # 测试环境用临时路径
    # 在Docker中运行时，可能会有asyncio事件循环冲突
    # 尝试直接运行
    try:
        asyncio.run(recorder.start())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Runtime error: {e}")
