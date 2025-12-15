#!/usr/bin/env python3
"""
Akshare Proxy API Service (Ultimate Robust - Json Fix + Baidu Valuation)
为内网环境提供 Akshare 数据访问接口
支持 EPIC-002 (Quant Strategy) 和 EPIC-005 (Backtesting) 的所有需求
Version: 2.5.0 (Add Baidu Valuation)
"""
from fastapi import FastAPI, HTTPException, Response
import akshare as ak
import logging
from datetime import datetime
import numpy as np
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Akshare Proxy API",
    description="Akshare 数据代理服务 (EPIC-002/005 Ready)",
    version="2.5.0"
)

def safe_json_response(df: pd.DataFrame) -> Response:
    """处理 DataFrame 并返回 JSON Response (解决 Date 序列化问题)"""
    if df is None or df.empty:
        return Response(content="[]", media_type="application/json")
    
    try:
        json_str = df.to_json(orient='records', date_format='iso', force_ascii=False)
        return Response(content=json_str, media_type="application/json")
    except Exception as e:
        logger.error(f"Serialization error: {e}")
        return Response(content="[]", status_code=500)

@app.get("/")
def root():
    return {"status": "running", "version": "2.5.0", "akshare_version": ak.__version__}

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat(), "akshare_version": ak.__version__}

# ==========================================
# 1. 市场行情 (Market Data)
# ==========================================

@app.get("/api/v1/stock/spot")
def get_stock_spot():
    """全市场实时行情"""
    try:
        df = ak.stock_zh_a_spot_em()
        return safe_json_response(df)
    except Exception as e:
        logger.error(f"Spot error: {e}")
        raise HTTPException(500, str(e))

@app.get("/api/v1/stock/hist/{symbol}")
def get_stock_hist(symbol: str, start_date: str, end_date: str, adjust: str = "qfq"):
    """历史行情"""
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, start_date=start_date, end_date=end_date, adjust=adjust)
        return safe_json_response(df)
    except Exception as e:
        logger.error(f"Hist error: {e}")
        return Response(content='{"error": "%s", "data": []}' % str(e).replace('"', "'"), status_code=500, media_type="application/json")

@app.get("/api/v1/stock/info/{symbol}")
def get_stock_info(symbol: str):
    """个股基本信息"""
    try:
        df = ak.stock_individual_info_em(symbol=symbol)
        data = {}
        for _, row in df.iterrows():
            data[row['item']] = row['value']
        import json
        return Response(content=json.dumps(data, ensure_ascii=False), media_type="application/json")
    except Exception as e:
        logger.error(f"Info error: {e}")
        raise HTTPException(500, str(e))

# ==========================================
# 2. 财务数据 (Financials)
# ==========================================

@app.get("/api/v1/finance/statements/{symbol}")
def get_finance_statements(symbol: str):
    """三大财务报表摘要"""
    try:
        df = ak.stock_financial_abstract(symbol=symbol)
        return safe_json_response(df)
    except Exception as e:
        logger.error(f"Finance abstract error: {e}")
        raise HTTPException(500, str(e))

@app.get("/api/v1/finance/sheet/{symbol}")
def get_finance_sheet(symbol: str, type: str = "main"):
    """详细财务报表"""
    try:
        func_map = {
            "income": getattr(ak, 'stock_profit_sheet_by_quarterly_em', None),
            "balance": getattr(ak, 'stock_balance_sheet_by_quarterly_em', None),
            "cash": getattr(ak, 'stock_cash_flow_sheet_by_quarterly_em', None),
            "main": getattr(ak, 'stock_financial_analysis_indicator', None)
        }
        func = func_map.get(type)
        if not func:
            raise HTTPException(400, f"Invalid type: {type}")
            
        df = func(symbol=symbol)
        return safe_json_response(df)
    except Exception as e:
        logger.error(f"Finance sheet {type} error: {e}")
        raise HTTPException(500, str(e))

# ==========================================
# 3. 估值数据 (Valuation)
# ==========================================

@app.get("/api/v1/valuation/history/{symbol}")
def get_valuation_history(symbol: str):
    """历史估值 (使用财务指标替代)"""
    try:
        df = ak.stock_financial_analysis_indicator(symbol=symbol)
        return safe_json_response(df)
    except Exception as e:
        logger.error(f"Valuation history error: {e}")
        # Dont raise 500, return empty list
        return Response(content="[]", media_type="application/json")

@app.get("/api/v1/valuation/baidu/{symbol}")
def get_valuation_baidu(symbol: str, indicator: str = "市盈率(TTM)"):
    """
    百度股市通估值 (History support for PE-TTM, PB, etc.)
    indicator: '市盈率(TTM)', '市净率', '市销率(TTM)', '总市值'
    """
    try:
        # akshare.stock_zh_valuation_baidu(symbol="600519", indicator="市盈率(TTM)", period="近十年")
        df = ak.stock_zh_valuation_baidu(symbol=symbol, indicator=indicator, period="近十年")
        return safe_json_response(df)
    except Exception as e:
        logger.error(f"Valuation baidu error: {e}")
        # Fallback empty
        return Response(content="[]", media_type="application/json")

# ==========================================
# 4. 行业与板块
# ==========================================

@app.get("/api/v1/industry/list")
def get_industry_list():
    try:
        df = ak.stock_board_industry_name_em()
        return safe_json_response(df)
    except Exception as e:
        logger.error(f"Industry list error: {e}")
        raise HTTPException(500, str(e))

@app.get("/api/v1/industry/cons/{board_code}")
def get_industry_cons(board_code: str):
    try:
        df = ak.stock_board_industry_cons_em(symbol=board_code)
        return safe_json_response(df)
    except Exception as e:
        logger.error(f"Industry cons error: {e}")
        raise HTTPException(500, str(e))

# ==========================================
# 5. 榜单数据
# ==========================================

@app.get("/api/v1/rank/hot")
def get_rank_hot():
    try:
        df = ak.stock_hot_rank_em()
        return safe_json_response(df)
    except Exception as e:
        logger.error(f"Rank hot error: {e}")
        raise HTTPException(500, str(e))

@app.get("/api/v1/rank/surge")
def get_rank_surge():
    try:
        df = ak.stock_hot_up_em()
        return safe_json_response(df)
    except Exception as e:
        logger.error(f"Rank surge error: {e}")
        raise HTTPException(500, str(e))

@app.get("/api/v1/rank/limit_up")
def get_rank_limit_up(date: str):
    try:
        df = ak.stock_zt_pool_em(date=date)
        return safe_json_response(df)
    except Exception as e:
        logger.error(f"Rank limit up error: {e}")
        raise HTTPException(500, str(e))

@app.get("/api/v1/rank/dragon_tiger")
def get_rank_dragon_tiger(date: str):
    try:
        df = ak.stock_lhb_detail_em(start_date=date, end_date=date)
        return safe_json_response(df)
    except Exception as e:
        logger.error(f"Rank lhb error: {e}")
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8111, timeout_keep_alive=30)
