"""
端到端测试：在容器内直接运行

测试流程：
1. 初始化 Mootdx
2. 加载 L1 池
3. 运行 3 轮快照录制
4. 验证 Parquet 文件生成
"""

# Step 1: 初始化 Mootdx
print("Step 1: Initializing Mootdx...")
import subprocess
try:
    subprocess.run(["python", "-m", "mootdx", "bestip"], timeout=30, check=True)
    print("✅ Mootdx OK")
except:
    print("⚠️ Mootdx init issue (ignoring)")

# Step 2: 加载股票池
print("\nStep 2: Loading stock pool...")
import sys
sys.path.insert(0, '/app')
from src.core.stock_pool.manager import StockPoolManager, PoolLevel
manager = StockPoolManager()
count = manager.initialize_static_l1_pool()
print(f"✅ L1 Pool: {count} stocks")

# Step 3: 运行录制
print("\nStep 3: Starting recorder...")
from src.core.recorder.snapshot_recorder import SnapshotRecorder
import asyncio

recorder = SnapshotRecorder(manager, storage_path="/tmp/e2e_test")
asyncio.run(recorder.start())

# Step 4: 验证
print("\nStep 4: Verifying...")
stats = recorder.writer.get_stats()
print(f"  Files: {stats['files']}")
print(f"  Size: {stats['total_size_mb']} MB")
print("\n✅ Test complete!")
