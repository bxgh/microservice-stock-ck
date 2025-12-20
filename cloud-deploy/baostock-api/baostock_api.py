#!/usr/bin/env python3
"""
Baostock Remote API Wrapper
Provides HTTP API interface for Baostock data source
"""
from fastapi import FastAPI, Query, HTTPException
from typing import Optional
import baostock as bs
import pandas as pd
from contextlib import asynccontextmanager
from datetime import datetime
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global lock for baostock session (not thread-safe)
bs_lock = asyncio.Lock()
bs_logged_in = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage baostock login/logout lifecycle"""
    global bs_logged_in
    
    # Startup: login to baostock
    lg = bs.login()
    if lg.error_code != '0':
        logger.error(f"Baostock login failed: {lg.error_msg}")
        raise Exception(f"Baostock login failed: {lg.error_msg}")
    
    bs_logged_in = True
    logger.info(f"Baostock login success: {lg.error_msg}")
    
    yield
    
    # Shutdown: logout
    bs.logout()
    bs_logged_in = False
    logger.info("Baostock logged out")

app = FastAPI(
    title="Baostock Remote API",
    description="HTTP API wrapper for Baostock data source",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy" if bs_logged_in else "unhealthy",
        "source": "baostock",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/history/kline/{symbol}")
async def get_kline(
    symbol: str,
    start_date: str = Query(..., description="YYYY-MM-DD", regex=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(..., description="YYYY-MM-DD", regex=r"^\d{4}-\d{2}-\d{2}$"),
    frequency: str = Query("d", description="d/w/m for daily/weekly/monthly"),
    adjust: str = Query("2", description="1=后复权 2=前复权 3=不复权")
):
    """
    Get historical K-line data for a stock
    
    Args:
        symbol: Stock code (e.g., 600519 or sh.600519)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        frequency: d=daily, w=weekly, m=monthly
        adjust: 1=后复权, 2=前复权, 3=不复权
    
    Returns:
        List of K-line records
    """
    async with bs_lock:
        try:
            # Normalize symbol format (000001 -> sh.000001)
            if not symbol.startswith(('sh.', 'sz.')):
                prefix = 'sh.' if symbol.startswith('6') else 'sz.'
                symbol = prefix + symbol
            
            fields = "date,open,high,low,close,volume,amount,pctChg,turn"
            rs = bs.query_history_k_data_plus(
                symbol, fields,
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag=adjust
            )
            
            if rs.error_code != '0':
                logger.warning(f"Baostock query failed: {rs.error_msg}")
                raise HTTPException(status_code=400, detail=rs.error_msg)
            
            data = []
            while rs.next():
                data.append(rs.get_row_data())
            
            df = pd.DataFrame(data, columns=rs.fields)
            logger.info(f"Query success: {symbol}, {len(df)} records")
            return df.to_dict(orient="records")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/index/cons/{index_code}")
async def get_index_constituents(
    index_code: str,
    date: Optional[str] = Query(None, description="YYYY-MM-DD")
):
    """
    Get index constituent stocks
    
    Args:
        index_code: Index code (e.g., 000300 for CSI 300, 000016 for SH50)
        date: Optional date (default: latest)
    
    Returns:
        List of constituent stocks
    """
    async with bs_lock:
        try:
            target_date = date or datetime.now().strftime("%Y-%m-%d")
            
            # Map index codes to query functions
            if '000300' in index_code or 'hs300' in index_code.lower():
                rs = bs.query_hs300_stocks(date=target_date)
            elif '000016' in index_code or 'sh50' in index_code.lower():
                rs = bs.query_sz50_stocks(date=target_date)
            elif '399006' in index_code or 'zz500' in index_code.lower():
                rs = bs.query_zz500_stocks(date=target_date)
            else:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported index: {index_code}. Supported: 000300(HS300), 000016(SH50), 399006(ZZ500)"
                )
            
            if rs.error_code != '0':
                raise HTTPException(status_code=400, detail=rs.error_msg)
            
            data = []
            while rs.next():
                data.append(rs.get_row_data())
            
            df = pd.DataFrame(data, columns=rs.fields)
            logger.info(f"Index {index_code} constituents: {len(df)} stocks")
            return df.to_dict(orient="records")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/industry/classify")
async def get_industry_classification(
    symbol: Optional[str] = None,
    date: Optional[str] = None
):
    """
    Get industry classification for stocks
    
    Args:
        symbol: Optional stock code to filter
        date: Optional date (YYYY-MM-DD), default: today
    
    Returns:
        List of industry classification records
    """
    async with bs_lock:
        try:
            target_date = date or datetime.now().strftime("%Y-%m-%d")
            rs = bs.query_stock_industry(date=target_date)
            
            if rs.error_code != '0':
                raise HTTPException(status_code=400, detail=rs.error_msg)
            
            data = []
            while rs.next():
                row = rs.get_row_data()
                # Filter by symbol if provided
                if symbol is None or symbol in row[1]:
                    data.append(row)
            
            df = pd.DataFrame(data, columns=rs.fields)
            logger.info(f"Industry data: {len(df)} records")
            return df.to_dict(orient="records")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )
