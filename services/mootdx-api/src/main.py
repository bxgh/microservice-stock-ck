"""
Mootdx API - 通达信数据源 REST API 服务

提供 mootdx 库的 HTTP REST 接口封装，支持：
- 实时行情
- 分笔成交
- 历史K线
- 股票列表
- 财务信息
- 除权除息
- 指数K线
"""
import asyncio
import logging
import sys
import os

# Ensure shared Libs are importable
sys.path.append("/app/libs/gsd-shared")

# -------------------------------------------------------------
# --- Monkeypatch: Force mootdx to use pytdx for connection ---
try:
    import tdxpy.hq
    import pytdx.hq
    # Use print/logging warning to ensure visibility
    print("⚡ Monkeypatching: Overwriting tdxpy.hq.TdxHq_API with pytdx.hq.TdxHq_API")
    tdxpy.hq.TdxHq_API = pytdx.hq.TdxHq_API
except Exception as e:
    print(f"Monkeypatch failed: {e}")
# -------------------------------------------------------------

# --- Monkeypatch: Global SOCKS5 Proxy Support ---
SOCKS_PROXY = os.getenv("SOCKS_PROXY") # Format: "host:port" e.g. "127.0.0.1:1080"
if SOCKS_PROXY:
    try:
        import socket
        import socks
        host, port = SOCKS_PROXY.split(":")
        socks.set_default_proxy(socks.SOCKS5, host, int(port))
        socket.socket = socks.socksocket
        print(f"⚡ SOCKS Proxy Enabled: Default socket configured to use {SOCKS_PROXY}")
    except Exception as e:
        print(f"❌ Failed to configure SOCKS proxy: {e}")
# -------------------------------------------------------------

import core.tdx_pool 
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from api.routes import router
from handlers.mootdx_handler import MootdxHandler
from workers.stream_worker import RedisStreamWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("mootdx-api")

# 全局 Handler 实例
mootdx_handler: MootdxHandler = None
stream_worker: RedisStreamWorker = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global mootdx_handler, stream_worker
    
    # 启动时初始化
    logger.info("Initializing Mootdx API...")
    mootdx_handler = MootdxHandler()
    await mootdx_handler.initialize()
    logger.info("✓ Mootdx API ready")
    
    # 启动 Redis Worker
    logger.info("Starting Redis Stream Worker...")
    stream_worker = RedisStreamWorker(mootdx_handler)
    await stream_worker.start()
    
    yield
    
    # 关闭时清理
    logger.info("Shutting down Mootdx API...")
    if stream_worker:
        await stream_worker.stop()
        
    if mootdx_handler:
        await mootdx_handler.close()
    logger.info("Mootdx API shutdown complete")


app = FastAPI(
    title="Mootdx API",
    description="通达信数据源 REST API",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """健康检查 - 包含连接池状态和 Worker 状态"""
    global mootdx_handler, stream_worker
    
    # Pool Status
    if mootdx_handler:
        pool_status = mootdx_handler.get_pool_status()
        is_healthy = pool_status.get("initialized", False)
    else:
        pool_status = {}
        is_healthy = False
        
    # Worker Status
    worker_ok = stream_worker and stream_worker.running
    
    return {
        "status": "healthy" if (is_healthy and worker_ok) else "unhealthy",
        "service": "mootdx-api",
        "pool": pool_status,
        "worker": "running" if worker_ok else "stopped"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "detail": "Internal server error"}
    )


def get_handler() -> MootdxHandler:
    """获取全局 Handler 实例"""
    global mootdx_handler
    return mootdx_handler


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
