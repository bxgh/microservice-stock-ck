"""
集成测试: 验证次新股多维对标策略全流程 (Target: 688802.SH)
"""
import pytest
import asyncio
import logging
import json
from src.orchestrator.orchestrator import StrategyOrchestrator
from src.orchestrator.report_generator import ReportGenerator

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_full_gsf_orchestration_688802():
    """验证 688802.SH 的完整分析流程"""
    target_code = "688802.SH"
    orchestrator = StrategyOrchestrator()
    
    print(f"\n🚀 开始执行全流程分析: {target_code}")
    
    # 1. 运行分析
    # 为了调试数据，我们直接在 Orchestrator 跑完后拿数据 (或者修改 orchestrator 支持返回数据)
    # 暂时通过外部模拟加载验证
    from src.orchestrator.data_loader import DataLoader
    loader = DataLoader()
    end_date = "2026-02-08"
    start_date = "2026-02-07"
    selection = await orchestrator.peer_selector.select_peers(target_code)
    print(f"Selection peers: {selection.peers[:10]}")
    data = await loader.load_strategy_data(target_code, selection.peers, start_date, end_date)
    print(f"Target DF count: {len(data['target'])}")
    print(f"Peers DF count: {len(data['peers'])}")
    if not data['peers'].empty:
        print(f"Peers data summary:\n{data['peers'].groupby('ts_code').size()}")
    
    result = await orchestrator.run_analysis(target_code, days_lookback=30, max_peers=20)
    
    if "error" in result:
        pytest.fail(f"分析执行失败: {result['error']}")
        
    print("\n✅ 分析执行成功")
    print(f"  行业: {result['target_info']['industry']}")
    print(f"  同类股数量: {result['peers']['count']}")
    
    # 2. 生成报告
    print("\n📝 正在生成 Markdown 报告...")
    report_md = ReportGenerator.generate_markdown(result)
    
    print("\n--- 报告预览 ---")
    print(report_md[:1000] + "..." if len(report_md) > 1000 else report_md)
    print("--- 预览结束 ---\n")
    
    # 3. 验证关键数据点
    assert result['target_info']['code'] == target_code
    assert result['peers']['count'] > 0, "应该找到至少一个同类股"
    
    # 验证是否有分布数据 (如果 ClickHouse 有特征数据的话)
    dist = result['analysis'].get('distribution', {})
    if not dist:
        print("⚠️ 警告: 未能获取到特征分布数据，请确认 ClickHouse features 表是否有数据。")
    else:
        print("🎉 成功获取到特征分布数据!")

if __name__ == "__main__":
    asyncio.run(test_full_gsf_orchestration_688802())
