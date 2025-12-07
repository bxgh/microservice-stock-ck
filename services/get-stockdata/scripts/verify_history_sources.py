# -*- coding: utf-8 -*-
"""
Story 007.04 数据源验证脚本

验证各数据源的历史K线获取能力：
1. mootdx 日线/分钟线
2. akshare stock_zh_a_hist (之前被拦截，重新测试)
3. baostock 日线/分钟线

@date: 2025-12-07
"""

import asyncio
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any

# 添加项目路径
sys.path.insert(0, '/app/src')

import pandas as pd


async def verify_mootdx_history():
    """验证 mootdx 历史K线能力 (使用 MootdxProvider)"""
    print("\n" + "=" * 60)
    print("📊 验证 mootdx 历史K线 (通过 MootdxProvider)")
    print("=" * 60)
    
    results = {}
    
    try:
        # 使用 MootdxProvider，会自动运行 bestip
        from data_sources.providers.mootdx_provider import MootdxProvider
        from data_sources.providers.base import DataType
        
        provider = MootdxProvider()
        
        # 初始化 (会触发 bestip)
        print("\n[0] 初始化 MootdxProvider...")
        if not await provider.initialize():
            print("   ❌ 初始化失败")
            results['init'] = {'success': False}
            return {'mootdx': results}
        print("   ✅ 初始化成功")
        results['init'] = {'success': True}
        
        # 获取底层 client 测试
        client = provider._client
        
        # 测试日线 (frequency=9)
        print("\n[1] 测试日线数据...")
        start = time.time()
        df_daily = client.bars(symbol='600519', frequency=9, offset=100)
        latency = (time.time() - start) * 1000
        
        if df_daily is not None and len(df_daily) > 0:
            print(f"   ✅ 日线成功: {len(df_daily)} 条, 耗时 {latency:.0f}ms")
            print(f"   字段: {list(df_daily.columns)}")
            print(f"   日期范围: {df_daily.index[0]} ~ {df_daily.index[-1]}")
            results['daily'] = {'success': True, 'count': len(df_daily), 'latency_ms': latency}
        else:
            print(f"   ❌ 日线失败: 无数据")
            results['daily'] = {'success': False}
        
        # 测试5分钟线 (frequency=8)
        print("\n[2] 测试5分钟线数据...")
        start = time.time()
        df_5min = client.bars(symbol='600519', frequency=8, offset=100)
        latency = (time.time() - start) * 1000
        
        if df_5min is not None and len(df_5min) > 0:
            print(f"   ✅ 5分钟线成功: {len(df_5min)} 条, 耗时 {latency:.0f}ms")
            print(f"   时间范围: {df_5min.index[0]} ~ {df_5min.index[-1]}")
            results['5min'] = {'success': True, 'count': len(df_5min), 'latency_ms': latency}
        else:
            print(f"   ❌ 5分钟线失败: 无数据")
            results['5min'] = {'success': False}
        
        # 测试历史深度
        print("\n[3] 测试历史深度 (日线800条)...")
        start = time.time()
        df_deep = client.bars(symbol='600519', frequency=9, offset=800)
        latency = (time.time() - start) * 1000
        
        if df_deep is not None and len(df_deep) > 0:
            print(f"   ✅ 深度测试: {len(df_deep)} 条, 耗时 {latency:.0f}ms")
            print(f"   最早日期: {df_deep.index[0]}")
            results['depth'] = {'success': True, 'count': len(df_deep), 'earliest': str(df_deep.index[0])}
        else:
            results['depth'] = {'success': False}
        
        # 关闭
        await provider.close()
            
    except Exception as e:
        import traceback
        print(f"   ❌ mootdx 错误: {e}")
        traceback.print_exc()
        results['error'] = str(e)
    
    return {'mootdx': results}


async def verify_akshare_history():
    """验证 akshare 历史K线能力 (之前被拦截)"""
    print("\n" + "=" * 60)
    print("📊 验证 akshare 历史K线 (stock_zh_a_hist)")
    print("=" * 60)
    
    results = {}
    
    try:
        import akshare as ak
        
        # 测试 stock_zh_a_hist - 之前被拦截的接口
        print("\n[1] 测试 stock_zh_a_hist...")
        start = time.time()
        
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None,
            lambda: ak.stock_zh_a_hist(
                symbol="600519",
                period="daily",
                start_date="20241001",
                end_date="20241231",
                adjust=""
            )
        )
        
        latency = (time.time() - start) * 1000
        
        if df is not None and len(df) > 0:
            print(f"   ✅ 成功: {len(df)} 条, 耗时 {latency:.0f}ms")
            print(f"   字段: {list(df.columns)}")
            print(f"   日期范围: {df['日期'].iloc[0]} ~ {df['日期'].iloc[-1]}")
            results['stock_zh_a_hist'] = {'success': True, 'count': len(df), 'latency_ms': latency}
        else:
            print(f"   ❌ 失败: 无数据")
            results['stock_zh_a_hist'] = {'success': False}
            
        # 测试分钟线
        print("\n[2] 测试分钟线 (stock_zh_a_hist 5分钟)...")
        start = time.time()
        
        df_min = await loop.run_in_executor(
            None,
            lambda: ak.stock_zh_a_hist_min_em(
                symbol="600519",
                period="5",
                adjust=""
            )
        )
        
        latency = (time.time() - start) * 1000
        
        if df_min is not None and len(df_min) > 0:
            print(f"   ✅ 成功: {len(df_min)} 条, 耗时 {latency:.0f}ms")
            print(f"   字段: {list(df_min.columns)}")
            results['minute'] = {'success': True, 'count': len(df_min), 'latency_ms': latency}
        else:
            print(f"   ❌ 失败: 无数据")
            results['minute'] = {'success': False}
            
    except Exception as e:
        print(f"   ❌ akshare 错误: {e}")
        results['error'] = str(e)
    
    return {'akshare': results}


async def verify_baostock_history():
    """验证 baostock 历史K线能力"""
    print("\n" + "=" * 60)
    print("📊 验证 baostock 历史K线")
    print("=" * 60)
    
    results = {}
    
    try:
        import baostock as bs
        
        # 登录
        print("\n[1] 尝试登录...")
        loop = asyncio.get_event_loop()
        lg = await loop.run_in_executor(None, bs.login)
        
        if lg.error_code != '0':
            print(f"   ❌ 登录失败: {lg.error_code} - {lg.error_msg}")
            print("   ⚠️  baostock 需要通过 proxychains4 运行!")
            results['login'] = {'success': False, 'error': lg.error_msg}
            return {'baostock': results}
        
        print(f"   ✅ 登录成功")
        results['login'] = {'success': True}
        
        # 测试日线
        print("\n[2] 测试日线数据...")
        start = time.time()
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        
        rs = await loop.run_in_executor(
            None,
            lambda: bs.query_history_k_data_plus(
                "sh.600519",
                "date,open,high,low,close,volume,amount,pctChg",
                start_date=start_date,
                end_date=end_date,
                frequency="d"
            )
        )
        
        latency = (time.time() - start) * 1000
        
        if rs.error_code == '0':
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            if len(data_list) > 0:
                df = pd.DataFrame(data_list, columns=rs.fields)
                print(f"   ✅ 日线成功: {len(df)} 条, 耗时 {latency:.0f}ms")
                print(f"   字段: {list(df.columns)}")
                print(f"   日期范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
                results['daily'] = {'success': True, 'count': len(df), 'latency_ms': latency}
            else:
                print(f"   ❌ 日线失败: 无数据")
                results['daily'] = {'success': False}
        else:
            print(f"   ❌ 查询失败: {rs.error_msg}")
            results['daily'] = {'success': False, 'error': rs.error_msg}
        
        # 测试5分钟线
        print("\n[3] 测试5分钟线数据...")
        start = time.time()
        
        rs_5min = await loop.run_in_executor(
            None,
            lambda: bs.query_history_k_data_plus(
                "sh.600519",
                "date,time,open,high,low,close,volume,amount",
                start_date=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                end_date=end_date,
                frequency="5"
            )
        )
        
        latency = (time.time() - start) * 1000
        
        if rs_5min.error_code == '0':
            data_list = []
            while rs_5min.next():
                data_list.append(rs_5min.get_row_data())
            
            if len(data_list) > 0:
                print(f"   ✅ 5分钟线成功: {len(data_list)} 条, 耗时 {latency:.0f}ms")
                results['5min'] = {'success': True, 'count': len(data_list), 'latency_ms': latency}
            else:
                print(f"   ❌ 5分钟线失败: 无数据")
                results['5min'] = {'success': False}
        else:
            print(f"   ❌ 查询失败: {rs_5min.error_msg}")
            results['5min'] = {'success': False}
        
        # 测试历史深度 (5年)
        print("\n[4] 测试历史深度 (5年数据)...")
        start = time.time()
        
        rs_deep = await loop.run_in_executor(
            None,
            lambda: bs.query_history_k_data_plus(
                "sh.600519",
                "date,close",
                start_date="2019-01-01",
                end_date=end_date,
                frequency="d"
            )
        )
        
        latency = (time.time() - start) * 1000
        
        if rs_deep.error_code == '0':
            data_list = []
            while rs_deep.next():
                data_list.append(rs_deep.get_row_data())
            
            if len(data_list) > 0:
                print(f"   ✅ 深度测试: {len(data_list)} 条 (5年), 耗时 {latency:.0f}ms")
                results['depth'] = {'success': True, 'count': len(data_list), 'latency_ms': latency}
            else:
                results['depth'] = {'success': False}
        else:
            results['depth'] = {'success': False}
        
        # 登出
        await loop.run_in_executor(None, bs.logout)
        print("\n   ✅ 已登出")
        
    except Exception as e:
        print(f"   ❌ baostock 错误: {e}")
        results['error'] = str(e)
    
    return {'baostock': results}


def print_summary(all_results: Dict[str, Any]):
    """打印验证总结"""
    print("\n" + "=" * 60)
    print("📋 验证总结")
    print("=" * 60)
    
    print("\n### 数据源能力对比\n")
    print("| 数据源 | 日线 | 分钟线 | 历史深度 | 备注 |")
    print("|--------|------|--------|----------|------|")
    
    # mootdx
    mootdx = all_results.get('mootdx', {})
    daily = "✅" if mootdx.get('daily', {}).get('success') else "❌"
    minute = "✅" if mootdx.get('5min', {}).get('success') else "❌"
    depth = mootdx.get('depth', {}).get('count', 'N/A')
    print(f"| mootdx | {daily} | {minute} | ~{depth}条 | 速度快 |")
    
    # akshare
    akshare = all_results.get('akshare', {})
    daily = "✅" if akshare.get('stock_zh_a_hist', {}).get('success') else "❌"
    minute = "✅" if akshare.get('minute', {}).get('success') else "❌"
    err = akshare.get('error', '')
    note = "被拦截" if "被拦截" in err or "403" in err or "Forbidden" in err else ""
    print(f"| akshare | {daily} | {minute} | 无限制 | {note} |")
    
    # baostock
    baostock = all_results.get('baostock', {})
    if baostock.get('login', {}).get('success'):
        daily = "✅" if baostock.get('daily', {}).get('success') else "❌"
        minute = "✅" if baostock.get('5min', {}).get('success') else "❌"
        depth = baostock.get('depth', {}).get('count', 'N/A')
        print(f"| baostock | {daily} | {minute} | ~{depth}条(5年) | 需proxy |")
    else:
        print(f"| baostock | ❌ | ❌ | N/A | 登录失败 |")
    
    print("\n### 推荐优先级\n")
    print("```")
    print("history_providers = [")
    print("    'mootdx',      # Priority 1: 速度快,稳定")
    print("    'baostock',    # Priority 2: 历史完整,需proxy")
    print("    'akshare',     # Priority 3: 如果可用")
    print("]")
    print("```")


async def main():
    """主函数"""
    print("=" * 60)
    print("  Story 007.04 历史数据源验证")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    all_results = {}
    
    # 1. 验证 mootdx
    result = await verify_mootdx_history()
    all_results.update(result)
    
    # 2. 验证 akshare
    result = await verify_akshare_history()
    all_results.update(result)
    
    # 3. 验证 baostock
    result = await verify_baostock_history()
    all_results.update(result)
    
    # 打印总结
    print_summary(all_results)
    
    return all_results


if __name__ == "__main__":
    asyncio.run(main())
