from fastapi import FastAPI, Query, HTTPException
import pywencai
import pandas as pd
from datetime import datetime
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pywencai-api")

app = FastAPI(title="Pywencai Remote API", version="1.0.0")

# 简单缓存实现
query_cache = {}
CACHE_TTL = 300  # 5分钟

@app.get("/health")
async def health():
    return {"status": "healthy", "source": "pywencai"}

@app.get("/api/v1/query")
async def query(
    q: str = Query(..., description="Natural language query"),
    perpage: int = Query(20, ge=1, le=100),
    nocache: bool = Query(False)
):
    cache_key = f"{q}:{perpage}"
    
    # 检查缓存
    if not nocache and cache_key in query_cache:
        cached_time, cached_data = query_cache[cache_key]
        if (datetime.now() - cached_time).total_seconds() < CACHE_TTL:
            logger.info(f"Cache hit for query: {q}")
            return {"data": cached_data, "cached": True}
    
    try:
        logger.info(f"Fetching data for query: {q}")
        # pywencai.get 是同步调用，可能需要在此处处理
        result = pywencai.get(query=q, perpage=perpage)
        
        if result is None:
            return {"data": [], "cached": False}
            
        data = result.to_dict(orient="records") if isinstance(result, pd.DataFrame) else result
        
        # 更新缓存
        query_cache[cache_key] = (datetime.now(), data)
        return {"data": data, "cached": False}
    
    except Exception as e:
        logger.error(f"Error querying pywencai: {e}")
        if "验证码" in str(e) or "CAPTCHA" in str(e):
            raise HTTPException(status_code=429, detail="CAPTCHA required, please try again later or check the server.")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
