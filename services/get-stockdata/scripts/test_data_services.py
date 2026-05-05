#!/usr/bin/env python3
"""
测试所有数据中台服务（内部功能测试）

直接测试Service层，无需API
"""

import asyncio
import sys
sys.path.insert(0, '/app/src')

async def test_quotes_service():
    """测试实时行情服务"""
    print("\n" + "="*60)
    print("TEST 1: Quotes Service (实时行情)")
    print("="*60)
    
    try:
        from data_services.quotes_service import QuotesService
        
        service = QuotesService()
        await service.initialize()
        print("✅ QuotesService initialized")
        
        # 测试获取实时行情
        result = await service.get_realtime_quotes(['000001', '600519'])
        if result.success:
            print(f"✅ get_realtime_quotes: {len(result.data)} stocks")
            if result.data:
                print(f"   Sample: {list(result.data.keys())[:2]}")
        else:
            print(f"⚠️ get_realtime_quotes failed: {result.error}")
        
        await service.close()
        return True
    except Exception as e:
        print(f"❌ Quotes Service error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_history_service():
    """测试历史数据服务"""
    print("\n" + "="*60)
    print("TEST 2: History Service (历史K线)")
    print("="*60)
    
    try:
        from data_services.history_service import HistoryService
        
        service = HistoryService()
        await service.initialize()
        print("✅ HistoryService initialized")
        
        # 测试获取历史K线
        result = await service.get_history(
            code='000001',
            period='daily',
            count=10
        )
        if result.success:
            print(f"✅ get_history: {len(result.data)} records")
            if len(result.data) > 0:
                print(f"   Latest: {result.data.iloc[-1].to_dict() if hasattr(result.data, 'iloc') else result.data}")
        else:
            print(f"⚠️ get_history failed: {result.error}")
        
        await service.close()
        return True
    except Exception as e:
        print(f"❌ History Service error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_ranking_service():
    """测试排行榜服务"""
    print("\n" + "="*60)
    print("TEST 3: Ranking Service (排行榜)")
    print("="*60)
    
    try:
        from data_services.ranking_service import RankingService
        
        service = RankingService()
        await service.initialize()
        print("✅ RankingService initialized")
        
        # 测试涨停榜
        result = await service.get_limit_up_stocks()
        if result.success:
            print(f"✅ get_limit_up_stocks: {len(result.data)} stocks")
            if len(result.data) > 0:
                print(f"   Sample: {result.data[:3] if isinstance(result.data, list) else list(result.data.head(3).to_dict('records'))}")
        else:
            print(f"⚠️ get_limit_up_stocks failed: {result.error}")
        
        await service.close()
        return True
    except Exception as e:
        print(f"❌ Ranking Service error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_index_service():
    """测试指数服务"""
    print("\n" + "="*60)
    print("TEST 4: Index Service (指数)")
    print("="*60)
    
    try:
        from data_services.index_service import IndexService
        
        service = IndexService()
        await service.initialize()
        print("✅ IndexService initialized")
        
        # 测试获取指数成分股
        result = await service.get_index_constituents('000300')  # 沪深300
        if result.success:
            print(f"✅ get_index_constituents: {len(result.data)} stocks")
        else:
            print(f"⚠️ get_index_constituents failed: {result.error}")
        
        await service.close()
        return True
    except Exception as e:
        print(f"❌ Index Service error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_sector_service():
    """测试板块服务"""
    print("\n" + "="*60)
    print("TEST 5: Sector Service (板块)")
    print("="*60)
    
    try:
        from data_services.sector_service import SectorService
        
        service = SectorService()
        await service.initialize()
        print("✅ SectorService initialized")
        
        # 测试获取行业板块
        result = await service.get_industry_sectors()
        if result.success:
            print(f"✅ get_industry_sectors: {len(result.data)} sectors")
        else:
            print(f"⚠️ get_industry_sectors failed: {result.error}")
        
        await service.close()
        return True
    except Exception as e:
        print(f"❌ Sector Service error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_tick_service():
    """测试分笔服务"""
    print("\n" + "="*60)
    print("TEST 6: Tick Service (分笔)")
    print("="*60)
    
    try:
        from data_services.tick_service import TickService
        
        service = TickService()
        await service.initialize()
        print("✅ TickService initialized")
        
        # 测试获取分笔数据
        result = await service.get_tick_data('000001', start=0, count=10)
        if result.success:
            print(f"✅ get_tick_data: {len(result.data)} ticks")
        else:
            print(f"⚠️ get_tick_data failed: {result.error}")
        
        await service.close()
        return True
    except Exception as e:
        print(f"❌ Tick Service error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_financial_service():
    """测试财务数据服务"""
    print("\n" + "="*60)
    print("TEST 7: Financial Service (财务)")
    print("="*60)
    
    try:
        from data_services.financial_service import FinancialService
        
        service = FinancialService()
        await service.initialize()
        print("✅ FinancialService initialized")
        
        # 测试获取财务数据
        result = await service.get_financial_report('000001')
        if result.success:
            print(f"✅ get_financial_report: success")
        else:
            print(f"⚠️ get_financial_report failed: {result.error}")
        
        await service.close()
        return True
    except Exception as e:
        print(f"❌ Financial Service error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_fund_flow_service():
    """测试资金流向服务"""
    print("\n" + "="*60)
    print("TEST 8: Fund Flow Service (资金流向)")
    print("="*60)
    
    try:
        from data_services.fund_flow_service import FundFlowService
        
        service = FundFlowService()
        await service.initialize()
        print("✅ FundFlowService initialized")
        
        # 测试获取资金流向
        result = await service.get_fund_flow('000001')
        if result.success:
            print(f"✅ get_fund_flow: success")
        else:
            print(f"⚠️ get_fund_flow failed: {result.error}")
        
        await service.close()
        return True
    except Exception as e:
        print(f"❌ Fund Flow Service error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """运行所有测试"""
    print("\n" + "🚀"*30)
    print("数据中台服务完整测试")
    print("🚀"*30)
    
    results = {}
    
    # 核心服务（P0）
    results['Quotes'] = await test_quotes_service()
    results['History'] = await test_history_service()
    results['Ranking'] = await test_ranking_service()
    
    # 重要服务（P1）
    results['Index'] = await test_index_service()
    results['Sector'] = await test_sector_service()
    results['Tick'] = await test_tick_service()
    
    # 高级服务（P2）
    results['Financial'] = await test_financial_service()
    results['FundFlow'] = await test_fund_flow_service()
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:15} {status}")
    
    print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 所有服务测试通过！")
    else:
        print(f"\n⚠️ {total - passed}个服务需要修复")

if __name__ == '__main__':
    asyncio.run(main())
