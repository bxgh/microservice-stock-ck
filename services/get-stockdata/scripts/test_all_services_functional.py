#!/usr/bin/env python3
"""
全新的功能测试 - 实际调用每个服务
不依赖已有测试，从头验证功能
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# 设置路径
sys.path.insert(0, '/app/src')
os.chdir('/app')

print("\n" + "=" * 80)
print("DATA SERVICES 完整功能测试")
print("=" * 80)
print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80 + "\n")

results = {}

# ============================================================================
# TEST 1: QuotesService
# ============================================================================
print("[TEST 1/8] QuotesService - 实时行情服务")
print("-" * 80)
try:
    from data_services import QuotesService
    
    async def test_quotes():
        service = QuotesService()
        
        # 初始化
        print("  [1.1] 初始化服务...")
        init_ok = await service.initialize()
        if not init_ok:
            print("      ❌ 初始化失败")
            return False
        print("      ✅ 初始化成功")
        
        # 获取实时行情
        print("  [1.2] 获取实时行情 (000001, 600519)...")
        result = await service.get_realtime_quotes(['000001', '600519'])
        if not result.success:
            print(f"      ❌ 失败: {result.error}")
            await service.close()
            return False
        
        if not result.data or len(result.data) == 0:
            print(f"      ❌ 返回空数据")
            await service.close()
            return False
        
        print(f"      ✅ 成功获取 {len(result.data)} 只股票")
        for code in list(result.data.keys())[:2]:
            quote = result.data[code]
            print(f"         {code}: {quote.get('name', 'N/A')} - {quote.get('price', 'N/A')}")
        
        await service.close()
        return True
    
    success = asyncio.run(test_quotes())
    results['QuotesService'] = success
    print(f"\n  结果: {'✅ PASS' if success else '❌ FAIL'}\n")
    
except Exception as e:
    print(f"  ❌ 异常: {type(e).__name__}: {e}\n")
    results['QuotesService'] = False

# ============================================================================
# TEST 2: HistoryService
# ============================================================================
print("[TEST 2/8] HistoryService - 历史K线服务")
print("-" * 80)
try:
    from data_services import HistoryService, AdjustType, Frequency
    
    async def test_history():
        service = HistoryService()
        
        # 初始化
        print("  [2.1] 初始化服务...")
        init_ok = await service.initialize()
        if not init_ok:
            print("      ❌ 初始化失败")
            return False
        print("      ✅ 初始化成功")
        
        # 获取日K线
        print("  [2.2] 获取日K线 (000001, 最近5天)...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)
        
        result = await service.get_daily(
            '000001',
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            adjust=AdjustType.QFQ
        )
        
        if not result.success:
            print(f"      ❌ 失败: {result.error}")
            await service.close()
            return False
        
        if result.data is None or len(result.data) == 0:
            print(f"      ❌ 返回空数据")
            await service.close()
            return False
        
        print(f"      ✅ 成功获取 {len(result.data)} 条K线")
        if hasattr(result.data, 'iloc') and len(result.data) > 0:
            latest = result.data.iloc[-1]
            print(f"         最新: date={latest.get('date', 'N/A')}, close={latest.get('close', 'N/A')}")
        
        await service.close()
        return True
    
    success = asyncio.run(test_history())
    results['HistoryService'] = success
    print(f"\n  结果: {'✅ PASS' if success else '❌ FAIL'}\n")
    
except Exception as e:
    print(f"  ❌ 异常: {type(e).__name__}: {e}\n")
    results['HistoryService'] = False

# ============================================================================
# TEST 3: RankingService
# ============================================================================
print("[TEST 3/8] RankingService - 排行榜服务")
print("-" * 80)
try:
    from data_services import RankingService
    
    async def test_ranking():
        service = RankingService()
        
        # 初始化
        print("  [3.1] 初始化服务...")
        init_ok = await service.initialize()
        if not init_ok:
            print("      ❌ 初始化失败")
            return False
        print("      ✅ 初始化成功")
        
        # 获取涨停股票
        print("  [3.2] 获取涨停股票...")
        result = await service.get_limit_up_stocks()
        
        if not result.success:
            print(f"      ❌ 失败: {result.error}")
            await service.close()
            return False
        
        print(f"      ✅ 成功获取 {len(result.data)} 只涨停股")
        if len(result.data) > 0:
            # 显示前3只
            for item in list(result.data)[:3]:
                if isinstance(item, dict):
                    print(f"         {item.get('code', 'N/A')}: {item.get('name', 'N/A')} +{item.get('change_pct', 'N/A')}%")
        
        await service.close()
        return True
    
    success = asyncio.run(test_ranking())
    results['RankingService'] = success
    print(f"\n  结果: {'✅ PASS' if success else '❌ FAIL'}\n")
    
except Exception as e:
    print(f"  ❌ 异常: {type(e).__name__}: {e}\n")
    results['RankingService'] = False

# ============================================================================
# TEST 4: IndexService
# ============================================================================
print("[TEST 4/8] IndexService - 指数服务")
print("-" * 80)
try:
    from data_services import IndexService
    
    async def test_index():
        service = IndexService()
        
        # 初始化
        print("  [4.1] 初始化服务...")
        init_ok = await service.initialize()
        if not init_ok:
            print("      ❌ 初始化失败")
            return False
        print("      ✅ 初始化成功")
        
        # 获取沪深300成分股
        print("  [4.2] 获取沪深300成分股...")
        result = await service.get_index_constituents('000300')
        
        if not result.success:
            print(f"      ❌ 失败: {result.error}")
            await service.close()
            return False
        
        if result.data is None or len(result.data) == 0:
            print(f"      ❌ 返回空数据")
            await service.close()
            return False
        
        print(f"      ✅ 成功获取 {len(result.data)} 只成分股")
        
        await service.close()
        return True
    
    success = asyncio.run(test_index())
    results['IndexService'] = success
    print(f"\n  结果: {'✅ PASS' if success else '❌ FAIL'}\n")
    
except Exception as e:
    print(f"  ❌ 异常: {type(e).__name__}: {e}\n")
    results['IndexService'] = False

# ============================================================================
# TEST 5: SectorService
# ============================================================================
print("[TEST 5/8] SectorService - 板块服务")
print("-" * 80)
try:
    from data_services import SectorService
    
    async def test_sector():
        service = SectorService()
        
        # 初始化
        print("  [5.1] 初始化服务...")
        init_ok = await service.initialize()
        if not init_ok:
            print("      ❌ 初始化失败")
            return False
        print("      ✅ 初始化成功")
        
        # 获取行业排行
        print("  [5.2] 获取行业排行...")
        result = await service.get_industry_ranking(limit=20)
        
        if not result.success:
            print(f"      ❌ 失败: {result.error}")
            await service.close()
            return False
        
        if result.data is None or len(result.data) == 0:
            print(f"      ❌ 返回空数据")
            await service.close()
            return False
        
        print(f"      ✅ 成功获取 {len(result.data)} 个行业")
        
        await service.close()
        return True
    
    success = asyncio.run(test_sector())
    results['SectorService'] = success
    print(f"\n  结果: {'✅ PASS' if success else '❌ FAIL'}\n")
    
except Exception as e:
    print(f"  ❌ 异常: {type(e).__name__}: {e}\n")
    results['SectorService'] = False

# ============================================================================
# TEST 6: TickService
# ============================================================================
print("[TEST 6/8] TickService - 分笔服务")
print("-" * 80)
try:
    from data_services import TickService
    
    async def test_tick():
        service = TickService()
        
        # 初始化
        print("  [6.1] 初始化服务...")
        init_ok = await service.initialize()
        if not init_ok:
            print("      ❌ 初始化失败")
            return False
        print("      ✅ 初始化成功")
        
        # 获取分笔数据
        print("  [6.2] 获取分笔数据 (000001, 最新10条)...")
        result = await service.get_tick_data('000001', start=0, count=10)
        
        if not result.success:
            print(f"      ❌ 失败: {result.error}")
            await service.close()
            return False
        
        if result.data is None or len(result.data) == 0:
            print(f"      ⚠️  返回空数据（可能非交易时间）")
            await service.close()
            return True  # 非交易时间返回空是正常的
        
        print(f"      ✅ 成功获取 {len(result.data)} 条分笔")
        
        await service.close()
        return True
    
    success = asyncio.run(test_tick())
    results['TickService'] = success
    print(f"\n  结果: {'✅ PASS' if success else '❌ FAIL'}\n")
    
except Exception as e:
    print(f"  ❌ 异常: {type(e).__name__}: {e}\n")
    results['TickService'] = False

# ============================================================================
# TEST 7: FinancialService
# ============================================================================
print("[TEST 7/8] FinancialService - 财务服务")
print("-" * 80)
try:
    from data_services import FinancialService
    
    async def test_financial():
        service = FinancialService()
        
        # 初始化
        print("  [7.1] 初始化服务...")
        init_ok = await service.initialize()
        if not init_ok:
            print("      ❌ 初始化失败")
            return False
        print("      ✅ 初始化成功")
        
        # 获取财务摘要
        print("  [7.2] 获取财务摘要 (000001)...")
        result = await service.get_financial_summary('000001')
        
        if not result.success:
            print(f"      ❌ 失败: {result.error}")
            await service.close()
            return False
        
        if result.data is None:
            print(f"      ❌ 返回空数据")
            await service.close()
            return False
        
        print(f"      ✅ 成功获取财务数据")
        
        await service.close()
        return True
    
    success = asyncio.run(test_financial())
    results['FinancialService'] = success
    print(f"\n  结果: {'✅ PASS' if success else '❌ FAIL'}\n")
    
except Exception as e:
    print(f"  ❌ 异常: {type(e).__name__}: {e}\n")
    results['FinancialService'] = False

# ============================================================================
# TEST 8: FundFlowService
# ============================================================================
print("[TEST 8/8] FundFlowService - 资金流向服务")
print("-" * 80)
try:
    from data_services import FundFlowService
    
    async def test_fund_flow():
        service = FundFlowService()
        
        # 初始化
        print("  [8.1] 初始化服务...")
        init_ok = await service.initialize()
        if not init_ok:
            print("      ❌ 初始化失败")
            return False
        print("      ✅ 初始化成功")
        
        # 获取资金流向
        print("  [8.2] 获取资金流向 (000001)...")
        today = datetime.now().strftime('%Y-%m-%d')
        result = await service.get_fund_flow('000001', today)
        
        if not result.success:
            print(f"      ❌ 失败: {result.error}")
            await service.close()
            return False
        
        if result.data is None:
            print(f"      ❌ 返回空数据")
            await service.close()
            return False
        
        print(f"      ✅ 成功获取资金流向数据")
        
        await service.close()
        return True
    
    success = asyncio.run(test_fund_flow())
    results['FundFlowService'] = success
    print(f"\n  结果: {'✅ PASS' if success else '❌ FAIL'}\n")
    
except Exception as e:
    print(f"  ❌ 异常: {type(e).__name__}: {e}\n")
    results['FundFlowService'] = False

# ============================================================================
# 总结
# ============================================================================
print("=" * 80)
print("测试总结")
print("=" * 80)

passed = sum(1 for v in results.values() if v)
total = len(results)

for service, result in results.items():
    status = "✅ PASS" if result else "❌ FAIL"
    print(f"  {service:20} {status}")

print("\n" + "-" * 80)
print(f"  总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
print("=" * 80 + "\n")

if passed == total:
    print("🎉 所有服务测试通过!\n")
    sys.exit(0)
else:
    print(f"⚠️  {total - passed} 个服务需要修复\n")
    sys.exit(1)
