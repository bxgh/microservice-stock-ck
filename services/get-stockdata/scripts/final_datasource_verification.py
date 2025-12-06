#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPIC-007 数据源最终验证脚本

验证所有5个数据源的可用性：
1. mootdx - 实时行情、分笔、K线
2. akshare - 榜单、指数成分、ETF
3. easyquotation - 实时行情备份
4. pywencai - 自然语言选股、板块涨幅
5. baostock - 历史K线 (需要 proxychains4)

用法:
  普通数据源: python scripts/final_datasource_verification.py
  含baostock: proxychains4 python scripts/final_datasource_verification.py
"""

import sys
import time
import asyncio
from datetime import datetime
from typing import List, Dict, Any

# 测试结果
results: List[Dict[str, Any]] = []


def log_result(source: str, api: str, status: str, rows: int = 0, 
               latency: float = 0, sample: str = None, error: str = None):
    """记录测试结果"""
    result = {
        "source": source,
        "api": api,
        "status": status,
        "rows": rows,
        "latency_ms": round(latency * 1000, 1),
        "sample": sample[:80] if sample else None,
        "error": error[:80] if error else None
    }
    results.append(result)
    
    icon = "✅" if status == "OK" else "❌" if status == "FAIL" else "⚠️"
    print(f"  {icon} [{source}] {api}: {status} ({rows} rows, {result['latency_ms']}ms)")
    if sample:
        print(f"      └─ {sample[:60]}")
    if error:
        print(f"      └─ Error: {error[:60]}")


def test_mootdx():
    """测试 mootdx"""
    print("\n" + "="*60)
    print("📊 1. 测试 mootdx (实时行情、分笔、K线)")
    print("="*60)
    
    try:
        from mootdx.quotes import Quotes
        
        # 连接
        start = time.time()
        try:
            client = Quotes.factory(market='std', bestip=True, timeout=10)
            latency = time.time() - start
            log_result("mootdx", "连接", "OK", latency=latency)
            
            # 实时行情
            start = time.time()
            quotes = client.quotes(symbol=['000001', '600519'])
            latency = time.time() - start
            if quotes is not None and len(quotes) > 0:
                price = quotes.iloc[0].get('price', 'N/A')
                sample = f"000001: 价格={price}"
                log_result("mootdx", "实时行情", "OK", rows=len(quotes), 
                          latency=latency, sample=sample)
            else:
                log_result("mootdx", "实时行情", "WARN", error="无数据")
            
            # K线数据
            start = time.time()
            bars = client.bars(symbol='000001', frequency=9, offset=0)
            latency = time.time() - start
            if bars is not None and len(bars) > 0:
                log_result("mootdx", "日线K线", "OK", rows=len(bars), latency=latency)
            else:
                log_result("mootdx", "日线K线", "WARN", error="无数据")
            
            # 分笔数据
            start = time.time()
            ticks = client.transactions(symbol='000001', start=0, offset=100)
            latency = time.time() - start
            if ticks is not None and len(ticks) > 0:
                log_result("mootdx", "分笔成交", "OK", rows=len(ticks), latency=latency)
            else:
                log_result("mootdx", "分笔成交", "WARN", error="无数据或非交易时段")
                
        except Exception as e:
            log_result("mootdx", "连接", "FAIL", error=str(e))
        
    except ImportError as e:
        log_result("mootdx", "import", "FAIL", error=f"未安装: {e}")


def test_akshare():
    """测试 akshare"""
    print("\n" + "="*60)
    print("📊 2. 测试 akshare (榜单、指数成分、ETF)")
    print("="*60)
    
    try:
        import akshare as ak
        
        tests = [
            ("人气榜", lambda: ak.stock_hot_rank_em()),
            ("涨停池", lambda: ak.stock_zt_pool_em(date="20241206")),
            ("龙虎榜", lambda: ak.stock_lhb_detail_em(start_date="20241205", end_date="20241206")),
            ("沪深300成分", lambda: ak.index_stock_cons(symbol="000300")),
        ]
        
        for name, func in tests:
            start = time.time()
            try:
                result = func()
                latency = time.time() - start
                if result is not None and len(result) > 0:
                    log_result("akshare", name, "OK", rows=len(result), latency=latency)
                else:
                    log_result("akshare", name, "WARN", error="返回空数据")
            except Exception as e:
                log_result("akshare", name, "FAIL", error=str(e))
                
    except ImportError as e:
        log_result("akshare", "import", "FAIL", error=f"未安装: {e}")


def test_easyquotation():
    """测试 easyquotation"""
    print("\n" + "="*60)
    print("📊 3. 测试 easyquotation (多源实时行情)")
    print("="*60)
    
    try:
        import easyquotation
        
        # 新浪行情
        start = time.time()
        try:
            quotation = easyquotation.use('sina')
            data = quotation.real(['000001', '600519', '300750'])
            latency = time.time() - start
            if data and len(data) > 0:
                sample = list(data.values())[0]
                sample_str = f"000001: {sample.get('name')} 价格={sample.get('now')}"
                log_result("easyquotation", "sina行情", "OK", rows=len(data), 
                          latency=latency, sample=sample_str)
            else:
                log_result("easyquotation", "sina行情", "WARN", error="返回空数据")
        except Exception as e:
            log_result("easyquotation", "sina行情", "FAIL", error=str(e))
        
        # 全市场快照
        start = time.time()
        try:
            quotation = easyquotation.use('sina')
            data = quotation.market_snapshot(prefix=True)
            latency = time.time() - start
            if data and len(data) > 0:
                log_result("easyquotation", "全市场快照", "OK", rows=len(data), latency=latency)
            else:
                log_result("easyquotation", "全市场快照", "WARN", error="返回空数据")
        except Exception as e:
            log_result("easyquotation", "全市场快照", "FAIL", error=str(e))
            
    except ImportError as e:
        log_result("easyquotation", "import", "FAIL", error=f"未安装: {e}")


def test_pywencai():
    """测试 pywencai"""
    print("\n" + "="*60)
    print("📊 4. 测试 pywencai (自然语言选股、板块)")
    print("="*60)
    
    try:
        import pywencai
        
        tests = [
            ("涨停股票", "今日涨停股票"),
            ("连板股", "连续涨停天数大于1"),
            ("行业涨幅榜", "今日行业涨幅榜"),
            ("概念涨幅榜", "今日概念涨幅榜"),
        ]
        
        for name, query in tests:
            start = time.time()
            try:
                result = pywencai.get(query=query, perpage=20)
                latency = time.time() - start
                if hasattr(result, 'shape') and len(result) > 0:
                    log_result("pywencai", name, "OK", rows=len(result), latency=latency)
                elif result is not None:
                    log_result("pywencai", name, "WARN", error=f"返回类型: {type(result).__name__}")
                else:
                    log_result("pywencai", name, "FAIL", error="返回None")
            except Exception as e:
                log_result("pywencai", name, "FAIL", error=str(e))
                
    except ImportError as e:
        log_result("pywencai", "import", "FAIL", error=f"未安装: {e}")


def test_baostock():
    """测试 baostock (需要 proxychains4)"""
    print("\n" + "="*60)
    print("📊 5. 测试 baostock (历史K线，需proxychains4)")
    print("="*60)
    
    try:
        import baostock as bs
        
        # 登录
        start = time.time()
        lg = bs.login()
        latency = time.time() - start
        
        if lg.error_code == '0':
            log_result("baostock", "登录", "OK", latency=latency)
            
            # 历史K线
            start = time.time()
            rs = bs.query_history_k_data_plus(
                "sh.600519", "date,open,high,low,close,volume,pctChg",
                start_date='2024-12-01', end_date='2024-12-06', frequency='d'
            )
            data = []
            while (rs.error_code == '0') and rs.next():
                data.append(rs.get_row_data())
            latency = time.time() - start
            
            if len(data) > 0:
                sample = f"最新: {data[-1][0]} 收盘:{data[-1][4]}"
                log_result("baostock", "历史K线", "OK", rows=len(data), 
                          latency=latency, sample=sample)
            else:
                log_result("baostock", "历史K线", "WARN", error="无数据")
            
            # 沪深300成分股
            start = time.time()
            rs = bs.query_hs300_stocks()
            data = []
            while (rs.error_code == '0') and rs.next():
                data.append(rs.get_row_data())
            latency = time.time() - start
            
            if len(data) > 0:
                log_result("baostock", "沪深300成分", "OK", rows=len(data), latency=latency)
            else:
                log_result("baostock", "沪深300成分", "WARN", error="无数据")
            
            bs.logout()
        else:
            log_result("baostock", "登录", "FAIL", 
                      error=f"{lg.error_code}: {lg.error_msg}")
            print("\n    ⚠️  baostock 需要通过 proxychains4 运行!")
            print("    用法: proxychains4 python scripts/final_datasource_verification.py")
                
    except ImportError as e:
        log_result("baostock", "import", "FAIL", error=f"未安装: {e}")


def print_summary():
    """打印汇总"""
    print("\n" + "="*60)
    print("📋 最终测试汇总")
    print("="*60)
    
    # 按数据源分组
    sources = {}
    for r in results:
        src = r["source"]
        if src not in sources:
            sources[src] = {"ok": 0, "warn": 0, "fail": 0}
        if r["status"] == "OK":
            sources[src]["ok"] += 1
        elif r["status"] == "WARN":
            sources[src]["warn"] += 1
        else:
            sources[src]["fail"] += 1
    
    print("\n| 数据源 | 成功 | 警告 | 失败 | 状态 |")
    print("|--------|------|------|------|------|")
    
    all_ok = True
    for src, stats in sources.items():
        total = stats["ok"] + stats["warn"] + stats["fail"]
        if stats["fail"] == 0 and stats["ok"] > 0:
            status = "✅ 可用"
        elif stats["ok"] > 0:
            status = "⚠️ 部分可用"
            all_ok = False
        else:
            status = "❌ 不可用"
            all_ok = False
        print(f"| {src} | {stats['ok']} | {stats['warn']} | {stats['fail']} | {status} |")
    
    print("\n" + "="*60)
    if all_ok:
        print("🎉 所有数据源验证通过！可以开始实施 EPIC-007")
    else:
        print("⚠️  部分数据源有问题，请检查上述详情")
    print("="*60)
    
    return all_ok


def main():
    print("="*60)
    print("🚀 EPIC-007 数据源最终验证")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    test_mootdx()
    test_akshare()
    test_easyquotation()
    test_pywencai()
    test_baostock()
    
    success = print_summary()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
