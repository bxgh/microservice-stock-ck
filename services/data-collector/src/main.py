"""
Data Collector Service - EPIC-010 Story 10.0
数据采集微服务入口
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from config.nacos import register_to_nacos, unregister_from_nacos
from config.settings import settings

from scheduler.jobs import daily_kline_job, collector, dual_writer, ck_writer, mysql_writer
from grpc_client.client import close_datasource_client

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 调度器实例
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

def setup_scheduler():
    """配置定时任务"""
    # 每日 18:00 执行日K线采集
    scheduler.add_job(
        daily_kline_job,
        'cron',
        hour=18,
        minute=0,
        id='daily_kline_job'
    )
    logger.info("✅ 已注册日K线采集任务 (每日 18:00)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("🚀 Data Collector 服务启动中...")
    
    # 1. 初始化资源 (DB Writers)
    await ck_writer.initialize()
    await mysql_writer.initialize()
    await collector.initialize()
    logger.info("✅ 数据库写入器和采集器已初始化")
    
    # 2. Nacos 注册
    await register_to_nacos()
    
    # 3. 配置调度器并启动
    setup_scheduler()
    scheduler.start()
    logger.info("✅ APScheduler 调度器已启动")
    
    yield
    
    # 关闭时
    logger.info("🛑 Data Collector 服务关闭中...")
    
    # 1. 停止调度器
    scheduler.shutdown()
    
    # 2. Nacos 注销
    await unregister_from_nacos()
    
    # 3. 释放资源
    await dual_writer.close()
    await close_datasource_client()
    logger.info("✅ 资源清理完成")


app = FastAPI(
    title="Data Collector",
    description="数据采集微服务 - 从真实数据源采集 A 股数据",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "data-collector",
        "scheduler": "running" if scheduler.running else "stopped",
        "jobs": len(scheduler.get_jobs())
    }


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "Data Collector",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
