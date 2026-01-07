#!/usr/bin/env python3
"""
Tier 1 验证测试：多节点数据差异性验证

目的：验证是否通过切换 TDX 服务器可以获取到缺失的 09:25 数据

使用方法：
    docker exec -it microservice-stock-mootdx-api python /app/test_multi_node.py

或者在容器外：
    docker run --rm --network host -v $(pwd):/app gsd-worker:latest python /app/test_multi_node.py
"""

import asyncio
import logging
from typing import List, Dict, Any
from mootdx.quotes import Quotes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 之前采集中缺失 09:25 数据的股票样本
PROBLEM_STOCKS = [
    "688561",  # 最早 09:39
    "002049",  # 返回 0 条
    "600058",  # 仅 1 条
    "000003",  # 仅下午盘
    "000044",  # 无早盘数据
    "600050",  # 无早盘数据
    "688045",  # 最早 09:30
]

TEST_DATE = 20260106  # 测试日期


async def create_client() -> Quotes:
    """创建新的 TDX 客户端（每次可能连接不同服务器）"""
    loop = asyncio.get_event_loop()
    client = await loop.run_in_executor(
        None,
        lambda: Quotes.factory(market='std', bestip=True)
    )
    return client


async def fetch_tick(client: Quotes, code: str, date: int) -> Dict[str, Any]:
    """获取分笔数据并返回统计信息"""
    loop = asyncio.get_event_loop()
    
    try:
        data = await loop.run_in_executor(
            None,
            lambda: client.transactions(symbol=code, date=date, start=0, offset=2000)
        )
        
        if data is None or len(data) == 0:
            return {"count": 0, "earliest": "N/A", "latest": "N/A"}
        
        # 获取时间范围
        times = data['time'].astype(str).tolist()
        earliest = min(times) if times else "N/A"
        latest = max(times) if times else "N/A"
        
        return {
            "count": len(data),
            "earliest": earliest,
            "latest": latest,
            "has_0925": any(t.startswith("09:25") for t in times)
        }
    except Exception as e:
        logger.error(f"获取 {code} 失败: {e}")
        return {"count": 0, "earliest": "ERROR", "latest": "ERROR", "error": str(e)}


async def test_multi_node_difference():
    """测试多次重连是否能获取不同数据"""
    
    print("=" * 60)
    print("Tier 1 验证测试：多节点数据差异性")
    print("=" * 60)
    print(f"测试日期: {TEST_DATE}")
    print(f"测试股票: {len(PROBLEM_STOCKS)} 只")
    print("=" * 60)
    
    results = {}
    
    # 进行 3 次独立测试，每次重新连接（可能选择不同服务器）
    for run in range(3):
        print(f"\n>>> 第 {run + 1} 次连接...")
        
        client = await create_client()
        logger.info(f"客户端已创建")
        
        for code in PROBLEM_STOCKS:
            stats = await fetch_tick(client, code, TEST_DATE)
            results.setdefault(code, []).append(stats)
            print(f"  {code}: {stats['count']} 条, 最早 {stats['earliest']}, 09:25={stats.get('has_0925', False)}")
        
        # 关闭连接
        # mootdx 没有显式关闭方法，等待下次循环重建
        await asyncio.sleep(1)
    
    # 分析结果
    print("\n" + "=" * 60)
    print("结果分析")
    print("=" * 60)
    
    improved = 0
    same = 0
    
    for code, runs in results.items():
        counts = [r['count'] for r in runs]
        has_0925 = [r.get('has_0925', False) for r in runs]
        
        # 检查是否有变化
        if len(set(counts)) > 1 or any(has_0925):
            status = "✅ 有差异/有改善"
            improved += 1
        else:
            status = "❌ 无变化"
            same += 1
        
        print(f"{code}: {status}")
        for i, r in enumerate(runs):
            print(f"    Run {i+1}: {r['count']} 条, 最早 {r['earliest']}, 09:25={r.get('has_0925', False)}")
    
    print("\n" + "=" * 60)
    print("结论")
    print("=" * 60)
    print(f"有改善: {improved}/{len(PROBLEM_STOCKS)} ({improved/len(PROBLEM_STOCKS)*100:.1f}%)")
    print(f"无变化: {same}/{len(PROBLEM_STOCKS)} ({same/len(PROBLEM_STOCKS)*100:.1f}%)")
    
    if improved / len(PROBLEM_STOCKS) > 0.2:
        print("\n🟢 建议: 继续实施 Tier 2（连接池优化）")
    else:
        print("\n🔴 建议: 放弃多节点方案，换服务器无实质效果")


if __name__ == "__main__":
    asyncio.run(test_multi_node_difference())
