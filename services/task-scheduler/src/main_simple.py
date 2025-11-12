"""
TaskScheduler 微服务组件 - 简化版启动文件
"""

import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="TaskScheduler",
    description="TaskScheduler 微服务组件",
    version="2.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "TaskScheduler",
        "version": "2.0.0"
    }


@app.get("/api/v1/stats")
async def get_stats():
    """获取服务统计信息"""
    return {
        "service": "TaskScheduler",
        "version": "2.0.0",
        "status": "running",
        "uptime": "unknown"
    }


@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "TaskScheduler Microservice API",
        "version": "2.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting TaskScheduler microservice...")
    uvicorn.run(
        "main_simple:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        log_level="info"
    )