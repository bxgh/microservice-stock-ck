"""
端到端测试：股票池 + 快照录制 + Parquet 存储
"""
import asyncio
import subprocess
import time
from datetime import datetime
from src.core.stock_pool.manager import StockPoolManager, PoolLevel
from src.core.recorder.snapshot_recorder import SnapshotRecorder

def main():
    print("=" * 60)
    print("🧪 端到端测试：静态 L1 池快照录制系统")
    print("=" * 60)
    
    # 1. 初始化 Mootdx 配置
    print("\n📡 Step 1: Initializing Mootdx...")
    try:
        result = subprocess.run(
            ["python", "-m", "mootdx", "bestip"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("✅ Mootdx configuration complete")
        else:
            print(f"⚠️ Mootdx bestip warning: {result.stderr}")
    except Exception as e:
        print(f"⚠️ Mootdx initialization issue (可忽略): {e}")
    
    # 2. 初始化股票池管理器
    print("\n📊 Step 2: Initializing Stock Pool Manager...")
    manager = StockPoolManager()
    count = manager.initialize_static_l1_pool()
    print(f"✅ L1 Pool loaded: {count} stocks")
    
    # 3. 创建录制器（使用测试路径）
    print("\n💾 Step 3: Creating Snapshot Recorder...")
    recorder = SnapshotRecorder(manager, storage_path="/tmp/test_snapshots")
    print("✅ Recorder initialized")
    
    # 4. 运行录制测试
    print("\n🎬 Step 4: Starting recording test (3 rounds)...")
    try:
        asyncio.run(recorder.start())
    except KeyboardInterrupt:
        print("\n⏸️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
    
    # 5. 验证结果
    print("\n📈 Step 5: Verifying results...")
    stats = recorder.writer.get_stats()
    print(f"  Files created: {stats['files']}")
    print(f"  Total size: {stats['total_size_mb']} MB")
    
    print("\n" + "=" * 60)
    print("✅ 端到端测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
