#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证额外数据源接口

测试: pywencai, easyquotation, baostock
"""

import sys
import time
from datetime import datetime
from typing import List, Dict, Any

# 测试结果
results: List[Dict[str, Any]] = []


def log_result(source: str, api: str, status: str, rows: int = 0, 
               latency: float = 0, columns: List[str] = None, error: str = None):
    """记录测试结果"""
    result = {
        "source": source,
        "api": api,
        "status": status,
        "rows": rows,
        "latency_ms": round(latency * 1000, 1),
        "columns": columns[:5] if columns else [],
        "error": error[:80] if error else None
    }
    results.append(result)
    
    icon = "✅" if status == "OK" else "❌" if status == "FAIL" else "⚠️"
    print(f"  {icon} [{source}] {api}: {status} ({rows} rows, {result['latency_ms']}ms)")
    if error:
        print(f"      └─ {error[:80]}")


def test_pywencai():
    """测试 pywencai (同花顺i问财)"""
    print("\n" + "="*60)
    print("📊 测试 pywencai (同花顺i问财)")
    print("="*60)
    
    try:
        import pywencai
        
        # 测试1: 简单查询
        start = time.time()
        try:
            result = pywencai.get(query='今日涨停的股票', loop=True)
            latency = time.time() - start
            
            if result is not None and len(result) > 0:
                log_result("pywencai", "今日涨停", "OK", 
                          rows=len(result), latency=latency,
                          columns=list(result.columns) if hasattr(result, 'columns') else [])
                print(f"      └─ 样本: {result.head(2).to_dict() if len(result) > 0 else 'N/A'}")
            else:
                log_result("pywencai", "今日涨停", "WARN", error="返回数据为空")
        except Exception as e:
            log_result("pywencai", "今日涨停", "FAIL", error=str(e))
        
        # 测试2: 连板查询
        start = time.time()
        try:
            result = pywencai.get(query='连续涨停天数大于2', loop=True)
            latency = time.time() - start
            
            if result is not None and len(result) > 0:
                log_result("pywencai", "连板查询", "OK", 
                          rows=len(result), latency=latency)
            else:
                log_result("pywencai", "连板查询", "WARN", error="返回数据为空")
        except Exception as e:
            log_result("pywencai", "连板查询", "FAIL", error=str(e))
        
        # 测试3: 基本面查询
        start = time.time()
        try:
            result = pywencai.get(query='市盈率小于20且市值大于100亿', loop=True)
            latency = time.time() - start
            
            if result is not None and len(result) > 0:
                log_result("pywencai", "基本面筛选", "OK", 
                          rows=len(result), latency=latency)
            else:
                log_result("pywencai", "基本面筛选", "WARN", error="返回数据为空")
        except Exception as e:
            log_result("pywencai", "基本面筛选", "FAIL", error=str(e))
            
    except ImportError as e:
        log_result("pywencai", "import", "FAIL", error=f"未安装: {e}")
        print("      └─ 安装命令: pip install pywencai")


def test_easyquotation():
    """测试 easyquotation (多源实时行情)"""
    print("\n" + "="*60)
    print("📊 测试 easyquotation (多源实时行情)")
    print("="*60)
    
    try:
        import easyquotation
        
        test_codes = ['000001', '600519', '300750']
        
        # 测试1: 新浪行情
        start = time.time()
        try:
            quotation = easyquotation.use('sina')
            data = quotation.real(test_codes)
            latency = time.time() - start
            
            if data and len(data) > 0:
                log_result("easyquotation", "sina 实时行情", "OK", 
                          rows=len(data), latency=latency,
                          columns=list(list(data.values())[0].keys()) if data else [])
                # 打印样本
                sample = list(data.values())[0] if data else {}
                print(f"      └─ 样本: code={sample.get('code')}, price={sample.get('now')}, name={sample.get('name')}")
            else:
                log_result("easyquotation", "sina 实时行情", "WARN", error="返回数据为空")
        except Exception as e:
            log_result("easyquotation", "sina 实时行情", "FAIL", error=str(e))
        
        # 测试2: 腾讯行情
        start = time.time()
        try:
            quotation = easyquotation.use('tencent')
            data = quotation.real(test_codes)
            latency = time.time() - start
            
            if data and len(data) > 0:
                log_result("easyquotation", "tencent 实时行情", "OK", 
                          rows=len(data), latency=latency)
            else:
                log_result("easyquotation", "tencent 实时行情", "WARN", error="返回数据为空")
        except Exception as e:
            log_result("easyquotation", "tencent 实时行情", "FAIL", error=str(e))
        
        # 测试3: 全市场行情
        start = time.time()
        try:
            quotation = easyquotation.use('sina')
            data = quotation.market_snapshot(prefix=True)  # 全市场快照
            latency = time.time() - start
            
            if data and len(data) > 0:
                log_result("easyquotation", "全市场快照", "OK", 
                          rows=len(data), latency=latency)
            else:
                log_result("easyquotation", "全市场快照", "WARN", error="返回数据为空")
        except Exception as e:
            log_result("easyquotation", "全市场快照", "FAIL", error=str(e))
            
    except ImportError as e:
        log_result("easyquotation", "import", "FAIL", error=f"未安装: {e}")
        print("      └─ 安装命令: pip install easyquotation")


def test_baostock():
    """测试 baostock (历史数据)"""
    print("\n" + "="*60)
    print("📊 测试 baostock (历史数据)")
    print("="*60)
    
    try:
        import baostock as bs
        
        # 登录
        start = time.time()
        lg = bs.login()
        latency = time.time() - start
        
        if lg.error_code == '0':
            log_result("baostock", "login", "OK", latency=latency)
        else:
            log_result("baostock", "login", "FAIL", error=lg.error_msg)
            return
        
        # 测试1: 历史K线
        start = time.time()
        try:
            rs = bs.query_history_k_data_plus(
                "sh.600519",
                "date,open,high,low,close,volume,amount",
                start_date='2024-11-01',
                end_date='2024-12-05',
                frequency="d"
            )
            data_list = []
            while (rs.error_code == '0') and rs.next():
                data_list.append(rs.get_row_data())
            latency = time.time() - start
            
            if len(data_list) > 0:
                log_result("baostock", "历史K线 (600519)", "OK", 
                          rows=len(data_list), latency=latency,
                          columns=rs.fields)
                print(f"      └─ 样本: {data_list[-1]}")
            else:
                log_result("baostock", "历史K线", "WARN", error="返回数据为空")
        except Exception as e:
            log_result("baostock", "历史K线", "FAIL", error=str(e))
        
        # 测试2: 沪深300成分股
        start = time.time()
        try:
            rs = bs.query_hs300_stocks()
            data_list = []
            while (rs.error_code == '0') and rs.next():
                data_list.append(rs.get_row_data())
            latency = time.time() - start
            
            if len(data_list) > 0:
                log_result("baostock", "沪深300成分股", "OK", 
                          rows=len(data_list), latency=latency)
            else:
                log_result("baostock", "沪深300成分股", "WARN", error="返回数据为空")
        except Exception as e:
            log_result("baostock", "沪深300成分股", "FAIL", error=str(e))
        
        # 测试3: 财务数据
        start = time.time()
        try:
            rs = bs.query_profit_data(code="sh.600519", year=2024, quarter=3)
            data_list = []
            while (rs.error_code == '0') and rs.next():
                data_list.append(rs.get_row_data())
            latency = time.time() - start
            
            if len(data_list) > 0:
                log_result("baostock", "财务数据 (600519)", "OK", 
                          rows=len(data_list), latency=latency,
                          columns=rs.fields)
            else:
                log_result("baostock", "财务数据", "WARN", error="返回数据为空或未披露")
        except Exception as e:
            log_result("baostock", "财务数据", "FAIL", error=str(e))
        
        # 登出
        bs.logout()
        
    except ImportError as e:
        log_result("baostock", "import", "FAIL", error=f"未安装: {e}")
        print("      └─ 安装命令: pip install baostock")


def print_summary():
    """打印汇总"""
    print("\n" + "="*60)
    print("📋 测试结果汇总")
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
    
    print("\n| 数据源 | 成功 | 警告 | 失败 | 建议 |")
    print("|--------|------|------|------|-----|")
    for src, stats in sources.items():
        total = stats["ok"] + stats["warn"] + stats["fail"]
        if stats["fail"] == 0 and stats["ok"] > 0:
            status = "✅ 推荐使用"
        elif stats["ok"] > 0:
            status = "⚠️ 部分可用"
        else:
            status = "❌ 无法使用"
        print(f"| {src} | {stats['ok']} | {stats['warn']} | {stats['fail']} | {status} |")
    
    print("\n" + "="*60)


def main():
    print("="*60)
    print("🚀 额外数据源接口验证")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    test_pywencai()
    test_easyquotation()
    test_baostock()
    
    print_summary()


if __name__ == "__main__":
    main()
