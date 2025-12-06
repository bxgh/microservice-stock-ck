#!/usr/bin/env python3
"""
Comprehensive Data Source Verification for EPIC-007
Tests all key APIs across different data categories
"""
import sys
sys.path.insert(0, '/app/src')

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time

def test_api(name, func, **kwargs):
    """Test an API and return result summary"""
    try:
        start = time.time()
        df = func(**kwargs)
        duration = time.time() - start
        
        if df is not None and not df.empty:
            cols = df.columns.tolist()[:5]
            return {
                'status': '✅',
                'rows': len(df),
                'time': f'{duration:.1f}s',
                'sample_cols': cols
            }
        else:
            return {'status': '⚠️', 'rows': 0, 'time': '-', 'sample_cols': []}
    except Exception as e:
        return {'status': '❌', 'error': str(e)[:50]}

print("="*70)
print("EPIC-007: Data Source Verification Matrix")
print("="*70)
print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

results = {}

# ==================== Category 1: Real-time Quotes ====================
print("\n📊 Category 1: Real-time Quotes (实时行情)")
print("-" * 50)

# 1.1 A股实时行情 (already know this fails)
# results['stock_zh_a_spot_em'] = test_api('A股实时', ak.stock_zh_a_spot_em)
# print(f"  stock_zh_a_spot_em: Known to FAIL (anti-scraping)")

# 1.2 沪深京A股 (alternative)
results['stock_sh_a_spot_em'] = test_api('上海A股', ak.stock_sh_a_spot_em)
print(f"  stock_sh_a_spot_em: {results['stock_sh_a_spot_em']}")

# ==================== Category 2: Historical Data ====================
print("\n📈 Category 2: Historical Data (历史数据)")
print("-" * 50)

# 2.1 个股日线
results['stock_zh_a_hist'] = test_api('个股日线', ak.stock_zh_a_hist, 
    symbol='000001', period='daily', start_date='20241201', end_date='20241205', adjust='qfq')
print(f"  stock_zh_a_hist: {results['stock_zh_a_hist']}")

# ==================== Category 3: Limit Up/Down ====================
print("\n🔥 Category 3: Limit Up/Down (涨跌停数据)")
print("-" * 50)

# 3.1 涨停池
results['stock_zt_pool_em'] = test_api('涨停池', ak.stock_zt_pool_em, date='20241204')
print(f"  stock_zt_pool_em: {results['stock_zt_pool_em']}")

# 3.2 跌停池
results['stock_zt_pool_dtgc_em'] = test_api('跌停池', ak.stock_zt_pool_dtgc_em, date='20241204')
print(f"  stock_zt_pool_dtgc_em: {results['stock_zt_pool_dtgc_em']}")

# 3.3 连板统计
results['stock_zt_pool_zbgc_em'] = test_api('炸板股池', ak.stock_zt_pool_zbgc_em, date='20241204')
print(f"  stock_zt_pool_zbgc_em: {results['stock_zt_pool_zbgc_em']}")

# ==================== Category 4: Dragon & Tiger ====================
print("\n🐉 Category 4: Dragon & Tiger List (龙虎榜)")
print("-" * 50)

results['stock_lhb_detail_em'] = test_api('龙虎榜详情', ak.stock_lhb_detail_em, 
    start_date='20241204', end_date='20241204')
print(f"  stock_lhb_detail_em: {results['stock_lhb_detail_em']}")

# ==================== Category 5: Fund Flow ====================
print("\n💰 Category 5: Fund Flow (资金流向)")
print("-" * 50)

results['stock_individual_fund_flow_rank'] = test_api('个股资金流排名', 
    ak.stock_individual_fund_flow_rank, indicator='今日')
print(f"  stock_individual_fund_flow_rank: {results['stock_individual_fund_flow_rank']}")

results['stock_sector_fund_flow_rank'] = test_api('板块资金流排名',
    ak.stock_sector_fund_flow_rank, indicator='今日', sector_type='行业资金流')
print(f"  stock_sector_fund_flow_rank: {results['stock_sector_fund_flow_rank']}")

# ==================== Category 6: Hot/Sentiment ====================
print("\n🔥 Category 6: Hot/Sentiment (热门/情绪)")
print("-" * 50)

results['stock_hot_rank_em'] = test_api('人气榜', ak.stock_hot_rank_em)
print(f"  stock_hot_rank_em: {results['stock_hot_rank_em']}")

results['stock_hot_up_em'] = test_api('飙升榜', ak.stock_hot_up_em)
print(f"  stock_hot_up_em: {results['stock_hot_up_em']}")

results['stock_changes_em'] = test_api('盘口异动', ak.stock_changes_em, symbol='火箭发射')
print(f"  stock_changes_em: {results['stock_changes_em']}")

# ==================== Category 7: Index/ETF ====================
print("\n📊 Category 7: Index/ETF (指数/ETF)")
print("-" * 50)

results['index_stock_cons'] = test_api('沪深300成分股', ak.index_stock_cons, symbol='000300')
print(f"  index_stock_cons: {results['index_stock_cons']}")

results['fund_portfolio_hold_em'] = test_api('ETF持仓', ak.fund_portfolio_hold_em, 
    symbol='512760', date='2024')
print(f"  fund_portfolio_hold_em: {results['fund_portfolio_hold_em']}")

# ==================== Category 8: Board/Sector ====================
print("\n🏢 Category 8: Board/Sector (板块数据)")
print("-" * 50)

results['stock_board_concept_name_em'] = test_api('概念板块列表', ak.stock_board_concept_name_em)
print(f"  stock_board_concept_name_em: {results['stock_board_concept_name_em']}")

results['stock_board_industry_name_em'] = test_api('行业板块列表', ak.stock_board_industry_name_em)
print(f"  stock_board_industry_name_em: {results['stock_board_industry_name_em']}")

# ==================== Summary ====================
print("\n" + "="*70)
print("SUMMARY")
print("="*70)

success = sum(1 for r in results.values() if r.get('status') == '✅')
warning = sum(1 for r in results.values() if r.get('status') == '⚠️')
failed = sum(1 for r in results.values() if r.get('status') == '❌')

print(f"✅ Success: {success}")
print(f"⚠️ Warning: {warning}")
print(f"❌ Failed: {failed}")
print(f"Total Tested: {len(results)}")
