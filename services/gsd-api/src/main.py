"""
GSD-API: 股票数据查询服务

提供只读查询API，不包含数据同步和处理逻辑
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GSD-API",
    description="股票数据查询服务 - 只读API",
    version="0.1.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from api import (
    quotes_routes,
    market_routes,
    stocks_routes,
    health_routes,
    valuation_routes,
    finance_routes,
    liquidity_routes
)

app.include_router(quotes_routes.router)
app.include_router(market_routes.router)
app.include_router(stocks_routes.router)
app.include_router(health_routes.router)
app.include_router(valuation_routes.router)
app.include_router(finance_routes.router)
app.include_router(liquidity_routes.router)

@app.get("/")
async def root():
    return {
        "service": "gsd-api",
        "version": "0.1.0",
        "description": "股票数据查询服务",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
