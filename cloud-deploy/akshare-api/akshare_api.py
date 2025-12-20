from fastapi import FastAPI, Query, HTTPException
import akshare as ak
import pandas as pd
import logging
from typing import Optional, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("akshare-api")

app = FastAPI(title="Akshare Remote API", version="1.0.0")

@app.get("/health")
async def health():
    return {"status": "healthy", "source": "akshare"}

@app.get("/api/v1/rank/hot")
async def hot_rank():
    """今日人气榜"""
    try:
        df = ak.stock_hot_rank_em()
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error fetching hot rank: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/valuation/{code}")
async def valuation(code: str):
    """个股估值数据"""
    try:
        # 这里使用示例接口，实际可能需要根据需求调整 akshare 接口
        df = ak.stock_value_params_em(symbol=code)
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error fetching valuation for {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/finance/{code}")
async def finance(code: str):
    """个股财务摘要"""
    try:
        df = ak.stock_financial_abstract_thm(symbol=code)
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error fetching finance for {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market/calendar")
async def calendar():
    """交易日历"""
    try:
        df = ak.tool_trade_date_hist_sina()
        return df.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error fetching calendar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
