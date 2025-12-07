#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPIC-007 数据服务基础设施 - 数据源验证脚本

在实施 DataServiceManager 之前，验证所有计划使用的数据源 API 可用性。

验证范围:
1. QuotesService: mootdx 实时行情
2. TickService: mootdx 分笔数据
3. HistoryService: mootdx 历史K线
4. RankingService: akshare 榜单 + 盘后数据
5. IndexService: akshare 指数成分/ETF
6. SectorService: akshare 板块数据

运行方式:
docker compose -f docker-compose.dev.yml exec get-stockdata-api python scripts/verify_epic007_data_sources.py
"""

import asyncio
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
from tabulate import tabulate


# 验证结果收集
verification_results: List[Dict[str, Any]] = []


def log_result(service: str, api_name: str, status: str, rows: int = 0, 
               latency: float = 0, columns: List[str] = None, error: str = None):
    """记录验证结果"""
    result = {
        "service": service,
        "api": api_name,
        "status": status,
        "rows": rows,
        "latency_ms": round(latency * 1000, 1),
        "columns": columns[:5] if columns else [],  # 只记录前5列
        "error": error[:100] if error else None
    }
    verification_results.append(result)
    
    # 实时打印
    status_icon = "✅" if status == "OK" else "❌" if status == "FAIL" else "⚠️"
    print(f"  {status_icon} [{service}] {api_name}: {status} ({rows} rows, {result['latency_ms']}ms)")
    if error:
        print(f"      └─ Error: {error[:80]}...")


async def verify_mootdx_quotes() -> None:
    """验证 mootdx 实时行情 (QuotesService)"""
    print("\n" + "="*60)
    print("📊 验证 QuotesService (mootdx 实时行情)")
    print("="*60)
    
    try:
        from mootdx.quotes import Quotes
        
        # 测试股票代码
        test_codes = [
            ("000001", 0),  # 平安银行 (深圳)
            ("600519", 1),  # 贵州茅台 (上海)
            ("300750", 0),  # 宁德时代 (创业板)
        ]
        
        # 1. 测试连接
        start = time.time()
        client = Quotes.factory(market='std')
        latency = time.time() - start
        log_result("QuotesService", "mootdx.connect", "OK", latency=latency)
        
        # 2. 测试批量行情
        start = time.time()
        codes = [(code, market) for code, market in test_codes]
        quotes = client.quotes(codes)
        latency = time.time() - start
        
        if quotes is not None and len(quotes) > 0:
            log_result("QuotesService", "mootdx.quotes (批量)", "OK", 
                      rows=len(quotes), latency=latency,
                      columns=list(quotes.columns) if hasattr(quotes, 'columns') else [])
            print(f"      └─ 样本数据: {quotes.iloc[0].to_dict() if len(quotes) > 0 else 'N/A'}")
        else:
            log_result("QuotesService", "mootdx.quotes (批量)", "FAIL", 
                      error="返回数据为空")
        
        # 3. 单只股票详细行情
        start = time.time()
        detail = client.quotes([("000001", 0)])
        latency = time.time() - start
        
        if detail is not None and len(detail) > 0:
            log_result("QuotesService", "mootdx.quotes (单只)", "OK",
                      rows=len(detail), latency=latency)
        
    except Exception as e:
        log_result("QuotesService", "mootdx", "FAIL", error=str(e))


async def verify_mootdx_tick() -> None:
    """验证 mootdx 分笔数据 (TickService)"""
    print("\n" + "="*60)
    print("📊 验证 TickService (mootdx 分笔成交)")
    print("="*60)
    
    try:
        from mootdx.quotes import Quotes
        
        client = Quotes.factory(market='std')
        
        # 测试分笔数据 (当日)
        start = time.time()
        # transaction 方法获取分笔
        ticks = client.transaction(symbol='000001', start=0, offset=100)
        latency = time.time() - start
        
        if ticks is not None and len(ticks) > 0:
            log_result("TickService", "mootdx.transaction (当日分笔)", "OK",
                      rows=len(ticks), latency=latency,
                      columns=list(ticks.columns) if hasattr(ticks, 'columns') else [])
            print(f"      └─ 字段: {list(ticks.columns)}")
        else:
            log_result("TickService", "mootdx.transaction", "WARN", 
                      error="返回数据为空 (可能非交易时段)")
        
        # 测试历史分笔
        start = time.time()
        # 尝试获取历史分笔 (使用 history_transaction)
        hist_ticks = client.transactions(symbol='000001', start=0, offset=100)
        latency = time.time() - start
        
        if hist_ticks is not None and len(hist_ticks) > 0:
            log_result("TickService", "mootdx.transactions (历史分笔)", "OK",
                      rows=len(hist_ticks), latency=latency)
        else:
            log_result("TickService", "mootdx.transactions", "WARN",
                      error="返回数据为空")
            
    except Exception as e:
        log_result("TickService", "mootdx", "FAIL", error=str(e))


async def verify_mootdx_history() -> None:
    """验证 mootdx 历史K线 (HistoryService)"""
    print("\n" + "="*60)
    print("📊 验证 HistoryService (mootdx 历史K线)")
    print("="*60)
    
    try:
        from mootdx.quotes import Quotes
        
        client = Quotes.factory(market='std')
        
        # 日线 (category=9 表示日线)
        start = time.time()
        daily = client.bars(symbol='000001', frequency=9, offset=30)
        latency = time.time() - start
        
        if daily is not None and len(daily) > 0:
            log_result("HistoryService", "mootdx.bars (日线)", "OK",
                      rows=len(daily), latency=latency,
                      columns=list(daily.columns) if hasattr(daily, 'columns') else [])
            print(f"      └─ 日期范围: {daily.index[0]} ~ {daily.index[-1]}")
        else:
            log_result("HistoryService", "mootdx.bars (日线)", "FAIL",
                      error="返回数据为空")
        
        # 5分钟线 (category=0 表示5分钟)
        start = time.time()
        minute5 = client.bars(symbol='000001', frequency=0, offset=48)
        latency = time.time() - start
        
        if minute5 is not None and len(minute5) > 0:
            log_result("HistoryService", "mootdx.bars (5分钟)", "OK",
                      rows=len(minute5), latency=latency)
        else:
            log_result("HistoryService", "mootdx.bars (5分钟)", "WARN",
                      error="返回数据为空")
        
        # 周线 (category=5)
        start = time.time()
        weekly = client.bars(symbol='000001', frequency=5, offset=20)
        latency = time.time() - start
        
        if weekly is not None and len(weekly) > 0:
            log_result("HistoryService", "mootdx.bars (周线)", "OK",
                      rows=len(weekly), latency=latency)
        
    except Exception as e:
        log_result("HistoryService", "mootdx", "FAIL", error=str(e))


async def verify_akshare_ranking() -> None:
    """验证 akshare 榜单数据 (RankingService)"""
    print("\n" + "="*60)
    print("📊 验证 RankingService (akshare 榜单)")
    print("="*60)
    
    try:
        import akshare as ak
        
        # 1. 人气榜
        start = time.time()
        try:
            hot_rank = ak.stock_hot_rank_em()
            latency = time.time() - start
            if hot_rank is not None and len(hot_rank) > 0:
                log_result("RankingService", "stock_hot_rank_em (人气榜)", "OK",
                          rows=len(hot_rank), latency=latency,
                          columns=list(hot_rank.columns))
            else:
                log_result("RankingService", "stock_hot_rank_em", "FAIL", error="空数据")
        except Exception as e:
            log_result("RankingService", "stock_hot_rank_em", "FAIL", error=str(e))
        
        # 2. 飙升榜
        start = time.time()
        try:
            surge = ak.stock_hot_up_em()
            latency = time.time() - start
            if surge is not None and len(surge) > 0:
                log_result("RankingService", "stock_hot_up_em (飙升榜)", "OK",
                          rows=len(surge), latency=latency)
            else:
                log_result("RankingService", "stock_hot_up_em", "FAIL", error="空数据")
        except Exception as e:
            log_result("RankingService", "stock_hot_up_em", "FAIL", error=str(e))
        
        # 3. 盘口异动
        start = time.time()
        try:
            anomaly = ak.stock_changes_em(symbol="火箭发射")
            latency = time.time() - start
            if anomaly is not None and len(anomaly) > 0:
                log_result("RankingService", "stock_changes_em (火箭发射)", "OK",
                          rows=len(anomaly), latency=latency,
                          columns=list(anomaly.columns))
            else:
                log_result("RankingService", "stock_changes_em", "WARN", 
                          error="空数据 (可能非交易时段)")
        except Exception as e:
            log_result("RankingService", "stock_changes_em", "FAIL", error=str(e))
        
        # 4. 涨停池 (盘后)
        start = time.time()
        try:
            zt_pool = ak.stock_zt_pool_em(date=datetime.now().strftime("%Y%m%d"))
            latency = time.time() - start
            if zt_pool is not None and len(zt_pool) > 0:
                log_result("RankingService", "stock_zt_pool_em (涨停池)", "OK",
                          rows=len(zt_pool), latency=latency,
                          columns=list(zt_pool.columns))
            else:
                log_result("RankingService", "stock_zt_pool_em", "WARN",
                          error="空数据 (非交易日或盘中)")
        except Exception as e:
            log_result("RankingService", "stock_zt_pool_em", "FAIL", error=str(e))
        
        # 5. 连板统计
        start = time.time()
        try:
            strong = ak.stock_zt_pool_strong_em(date=datetime.now().strftime("%Y%m%d"))
            latency = time.time() - start
            if strong is not None and len(strong) > 0:
                log_result("RankingService", "stock_zt_pool_strong_em (连板)", "OK",
                          rows=len(strong), latency=latency)
            else:
                log_result("RankingService", "stock_zt_pool_strong_em", "WARN",
                          error="空数据")
        except Exception as e:
            log_result("RankingService", "stock_zt_pool_strong_em", "FAIL", error=str(e))
        
        # 6. 龙虎榜
        start = time.time()
        try:
            # 尝试获取最近交易日的龙虎榜
            lhb = ak.stock_lhb_detail_em(
                start_date=(datetime.now() - timedelta(days=7)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d")
            )
            latency = time.time() - start
            if lhb is not None and len(lhb) > 0:
                log_result("RankingService", "stock_lhb_detail_em (龙虎榜)", "OK",
                          rows=len(lhb), latency=latency,
                          columns=list(lhb.columns))
            else:
                log_result("RankingService", "stock_lhb_detail_em", "WARN",
                          error="空数据")
        except Exception as e:
            log_result("RankingService", "stock_lhb_detail_em", "FAIL", error=str(e))
            
    except ImportError as e:
        log_result("RankingService", "akshare import", "FAIL", error=str(e))


async def verify_akshare_index() -> None:
    """验证 akshare 指数/ETF (IndexService)"""
    print("\n" + "="*60)
    print("📊 验证 IndexService (akshare 指数/ETF)")
    print("="*60)
    
    try:
        import akshare as ak
        
        # 1. 沪深300成分股
        start = time.time()
        try:
            hs300 = ak.index_stock_cons(symbol="000300")
            latency = time.time() - start
            if hs300 is not None and len(hs300) > 0:
                log_result("IndexService", "index_stock_cons (沪深300)", "OK",
                          rows=len(hs300), latency=latency,
                          columns=list(hs300.columns))
            else:
                log_result("IndexService", "index_stock_cons", "FAIL", error="空数据")
        except Exception as e:
            log_result("IndexService", "index_stock_cons (沪深300)", "FAIL", error=str(e))
        
        # 2. 中证500成分股
        start = time.time()
        try:
            zz500 = ak.index_stock_cons(symbol="000905")
            latency = time.time() - start
            if zz500 is not None and len(zz500) > 0:
                log_result("IndexService", "index_stock_cons (中证500)", "OK",
                          rows=len(zz500), latency=latency)
        except Exception as e:
            log_result("IndexService", "index_stock_cons (中证500)", "FAIL", error=str(e))
        
        # 3. ETF持仓
        start = time.time()
        try:
            # 沪深300ETF (510300) 持仓
            etf_hold = ak.fund_portfolio_hold_em(symbol="510300", date="2024")
            latency = time.time() - start
            if etf_hold is not None and len(etf_hold) > 0:
                log_result("IndexService", "fund_portfolio_hold_em (ETF持仓)", "OK",
                          rows=len(etf_hold), latency=latency,
                          columns=list(etf_hold.columns))
            else:
                log_result("IndexService", "fund_portfolio_hold_em", "WARN", error="空数据")
        except Exception as e:
            log_result("IndexService", "fund_portfolio_hold_em", "FAIL", error=str(e))
            
    except ImportError as e:
        log_result("IndexService", "akshare import", "FAIL", error=str(e))


async def verify_akshare_sector() -> None:
    """验证 akshare 板块数据 (SectorService)"""
    print("\n" + "="*60)
    print("📊 验证 SectorService (akshare 板块)")
    print("="*60)
    
    try:
        import akshare as ak
        
        # 1. 行业板块行情
        start = time.time()
        try:
            industry = ak.stock_board_industry_name_em()
            latency = time.time() - start
            if industry is not None and len(industry) > 0:
                log_result("SectorService", "stock_board_industry_name_em (行业)", "OK",
                          rows=len(industry), latency=latency,
                          columns=list(industry.columns))
            else:
                log_result("SectorService", "stock_board_industry_name_em", "FAIL", error="空数据")
        except Exception as e:
            log_result("SectorService", "stock_board_industry_name_em", "FAIL", error=str(e))
        
        # 2. 概念板块行情
        start = time.time()
        try:
            concept = ak.stock_board_concept_name_em()
            latency = time.time() - start
            if concept is not None and len(concept) > 0:
                log_result("SectorService", "stock_board_concept_name_em (概念)", "OK",
                          rows=len(concept), latency=latency)
            else:
                log_result("SectorService", "stock_board_concept_name_em", "FAIL", error="空数据")
        except Exception as e:
            log_result("SectorService", "stock_board_concept_name_em", "FAIL", error=str(e))
        
        # 3. 板块成分股 (行业)
        start = time.time()
        try:
            # 获取第一个行业的成分股
            industry_cons = ak.stock_board_industry_cons_em(symbol="半导体")
            latency = time.time() - start
            if industry_cons is not None and len(industry_cons) > 0:
                log_result("SectorService", "stock_board_industry_cons_em (成分股)", "OK",
                          rows=len(industry_cons), latency=latency,
                          columns=list(industry_cons.columns))
            else:
                log_result("SectorService", "stock_board_industry_cons_em", "FAIL", error="空数据")
        except Exception as e:
            log_result("SectorService", "stock_board_industry_cons_em", "FAIL", error=str(e))
        
        # 4. 板块成分股 (概念)
        start = time.time()
        try:
            concept_cons = ak.stock_board_concept_cons_em(symbol="人工智能")
            latency = time.time() - start
            if concept_cons is not None and len(concept_cons) > 0:
                log_result("SectorService", "stock_board_concept_cons_em (概念成分)", "OK",
                          rows=len(concept_cons), latency=latency)
            else:
                log_result("SectorService", "stock_board_concept_cons_em", "FAIL", error="空数据")
        except Exception as e:
            log_result("SectorService", "stock_board_concept_cons_em", "FAIL", error=str(e))
            
    except ImportError as e:
        log_result("SectorService", "akshare import", "FAIL", error=str(e))


def generate_report() -> str:
    """生成验证报告"""
    print("\n" + "="*60)
    print("📋 验证报告汇总")
    print("="*60)
    
    # 统计
    total = len(verification_results)
    ok_count = sum(1 for r in verification_results if r["status"] == "OK")
    warn_count = sum(1 for r in verification_results if r["status"] == "WARN")
    fail_count = sum(1 for r in verification_results if r["status"] == "FAIL")
    
    print(f"\n总计测试: {total} 个 API")
    print(f"  ✅ 成功: {ok_count}")
    print(f"  ⚠️ 警告: {warn_count}")
    print(f"  ❌ 失败: {fail_count}")
    
    # 按服务分组
    services = {}
    for r in verification_results:
        svc = r["service"]
        if svc not in services:
            services[svc] = {"ok": 0, "warn": 0, "fail": 0, "apis": []}
        services[svc][r["status"].lower()] = services[svc].get(r["status"].lower(), 0) + 1
        services[svc]["apis"].append(r)
    
    print("\n按服务分组:")
    for svc, data in services.items():
        status = "✅" if data.get("fail", 0) == 0 else "❌"
        print(f"  {status} {svc}: OK={data.get('ok', 0)}, WARN={data.get('warn', 0)}, FAIL={data.get('fail', 0)}")
    
    # 生成 Markdown 报告
    report = f"""# EPIC-007 数据源验证报告

**验证时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**环境**: Docker 容器

## 📊 验证结果汇总

| 指标 | 数量 |
|-----|------|
| 总测试 | {total} |
| ✅ 成功 | {ok_count} |
| ⚠️ 警告 | {warn_count} |
| ❌ 失败 | {fail_count} |

## 📋 详细结果

| 服务 | API | 状态 | 行数 | 延迟(ms) | 备注 |
|-----|-----|------|------|---------|------|
"""
    
    for r in verification_results:
        status_icon = "✅" if r["status"] == "OK" else "❌" if r["status"] == "FAIL" else "⚠️"
        note = r["error"] if r["error"] else f"字段: {', '.join(r['columns'])}" if r["columns"] else ""
        report += f"| {r['service']} | {r['api']} | {status_icon} | {r['rows']} | {r['latency_ms']} | {note[:50]} |\n"
    
    report += f"""
## 🎯 服务可用性评估

| 服务 | 可用性 | 建议 |
|-----|--------|------|
"""
    
    for svc, data in services.items():
        if data.get("fail", 0) == 0:
            availability = "✅ 完全可用"
            suggestion = "可以开始实施"
        elif data.get("ok", 0) > 0:
            availability = "⚠️ 部分可用"
            suggestion = "需要调整数据源策略"
        else:
            availability = "❌ 不可用"
            suggestion = "需要替代方案"
        report += f"| {svc} | {availability} | {suggestion} |\n"
    
    return report


async def main():
    """主函数"""
    print("="*60)
    print("🚀 EPIC-007 数据服务基础设施 - 数据源验证")
    print(f"   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 依次验证各个服务
    await verify_mootdx_quotes()
    await verify_mootdx_tick()
    await verify_mootdx_history()
    await verify_akshare_ranking()
    await verify_akshare_index()
    await verify_akshare_sector()
    
    # 生成报告
    report = generate_report()
    
    # 保存报告
    report_path = "/app/docs/reports/epic007_data_source_verification.md"
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n📄 报告已保存: {report_path}")
    except Exception as e:
        print(f"\n⚠️ 保存报告失败: {e}")
        print("\n--- 报告内容 ---")
        print(report)
    
    # 返回状态码
    fail_count = sum(1 for r in verification_results if r["status"] == "FAIL")
    return 1 if fail_count > 5 else 0  # 失败超过5个视为严重问题


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
