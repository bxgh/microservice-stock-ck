"""
GSD-API: 股票数据查询服务 - 最小化版本

仅包含健康检查端点，用于集成测试
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

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

# 服务启动时间
start_time = datetime.now()

@app.get("/")
async def root():
    return {
        "service": "gsd-api",
        "version": "0.1.0",
        "description": "股票数据查询服务",
        "docs": "/docs"
    }

@app.get("/api/v1/health")
async def health_check():
    """健康检查端点"""
    uptime = int((datetime.now() - start_time).total_seconds())
    return {
        "success": True,
        "message": "Service health check completed",
        "data": {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "0.1.0",
            "uptime": uptime,
            "checks": {
                "framework": {
                    "status": "pass",
                    "message": "FastAPI framework is running"
                }
            }
        }
    }

@app.get("/api/v1/ready")
async def readiness_check():
    """就绪检查端点"""
    return {
        "success": True,
        "message": "Service is ready",
        "data": {
            "status": "ready",
            "timestamp": datetime.now().isoformat()
        }
    }

@app.get("/api/v1/live")
async def liveness_check():
    """存活检查端点"""
    uptime = int((datetime.now() - start_time).total_seconds())
    return {
        "success": True,
        "message": "Service is alive",
        "data": {
            "status": "alive",
            "timestamp": datetime.now().isoformat(),
            "uptime": uptime
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
