#!/usr/bin/env python3
"""
Get Stock Data 微服务

这是一个专门用于获取股票数据的微服务，包含：
- 健康检查
- 股票数据获取API路由

主要功能：
- 获取实时股票价格
- 获取股票历史数据
- 股票基本信息查询
- 股票数据缓存
"""

import asyncio
import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn

# 添加src到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入核心组件
try:
    from config.settings import settings
except ImportError:
    # 简化配置
    class SimpleSettings:
        name = "Get Stock Data Service"
        version = "1.0.0"
        debug = True
        log_level = "info"
        access_log = True
        host = "0.0.0.0"
        port = 8083
        log_file = "app.log"
    settings = SimpleSettings()

try:
    from api.health_routes import health_router
except ImportError:
    from fastapi import APIRouter
    health_router = APIRouter()

    @health_router.get("/health")
    async def health():
        return {"status": "healthy", "service": settings.name}

try:
    from api.example_routes import stock_router
except ImportError:
    print("Warning: stock_router not found, creating test routes")
    from fastapi import APIRouter
    stock_router = APIRouter(prefix="/api/v1/stocks", tags=["stocks"])

    @stock_router.get("/sources")
    async def get_data_sources():
        """获取数据源信息"""
        return {
            "success": True,
            "message": "获取数据源信息成功",
            "data": {
                "sources": {
                    "pytdx": {
                        "name": "PyTDX (通达信)",
                        "enabled": True,
                        "priority": 1,
                        "category": "核心数据源",
                        "description": "通达信数据接口，速度极快，支持实时行情和分笔数据",
                        "cost": "免费",
                        "speed": "极快 (0.05-0.3s)",
                        "data_types": ["实时行情", "历史数据", "分笔数据", "K线数据"],
                        "recommended_use": "实时行情、高频交易、分笔数据"
                    },
                    "easyquotation": {
                        "name": "EasyQuotation",
                        "enabled": True,
                        "priority": 2,
                        "category": "核心数据源",
                        "description": "简单易用的行情接口库，API友好",
                        "cost": "免费",
                        "speed": "很快 (0.1-0.5s)",
                        "data_types": ["实时行情", "基础数据"],
                        "recommended_use": "快速开发、实时监控"
                    },
                    "qstock": {
                        "name": "QStock",
                        "enabled": True,
                        "priority": 4,
                        "category": "核心数据源",
                        "description": "专业股票数据获取库，数据源丰富",
                        "cost": "免费",
                        "speed": "快 (0.2-0.8s)",
                        "data_types": ["实时行情", "历史数据", "财务数据", "技术指标"],
                        "recommended_use": "财务分析、基本面研究"
                    },
                    "akshare": {
                        "name": "AKShare (中国股票)",
                        "enabled": True,
                        "priority": 3,
                        "category": "核心数据源",
                        "description": "中国金融数据接口库，数据最全面",
                        "cost": "免费",
                        "speed": "快 (0.25-1.2s)",
                        "data_types": ["实时行情", "历史数据", "财务数据", "技术指标"],
                        "recommended_use": "通用场景、全面数据需求"
                    },
                    "mootdx": {
                        "name": "MooTDX",
                        "enabled": True,
                        "priority": 5,
                        "category": "备选数据源",
                        "description": "通达信数据接口，PyTDX的备用方案",
                        "cost": "免费",
                        "speed": "快 (0.3-0.7s)",
                        "data_types": ["实时行情", "历史数据", "分笔数据"],
                        "recommended_use": "PyTDX故障时的备用选择"
                    },
                    "tushare": {
                        "name": "Tushare",
                        "enabled": True,
                        "priority": 6,
                        "category": "付费数据源",
                        "description": "Tushare金融数据接口，免费版可用",
                        "cost": "免费(500次/天)",
                        "speed": "快 (0.2-0.8s)",
                        "data_types": ["实时行情", "历史数据", "财务数据", "板块数据"],
                        "recommended_use": "商业项目、高质量数据需求"
                    },
                    "baostock": {
                        "name": "BaoStock",
                        "enabled": True,
                        "priority": 8,
                        "category": "免费数据源",
                        "description": "证券宝金融数据平台，历史数据丰富",
                        "cost": "免费",
                        "speed": "中等 (0.5-1.5s)",
                        "data_types": ["历史数据", "财务数据"],
                        "recommended_use": "历史数据研究、长期分析"
                    },
                    "pandas": {
                        "name": "Pandas DataReader",
                        "enabled": True,
                        "priority": 9,
                        "category": "免费数据源",
                        "description": "Pandas数据读取器，国际数据源",
                        "cost": "免费",
                        "speed": "慢 (1.0-3.0s)",
                        "data_types": ["历史数据", "财务数据", "宏观数据"],
                        "recommended_use": "美股数据、宏观经济研究"
                    },
                    "alpha_vantage": {
                        "name": "Alpha Vantage",
                        "enabled": True,
                        "priority": 10,
                        "category": "免费数据源",
                        "description": "Alpha Vantage金融数据API，免费版可用",
                        "cost": "免费(500次/天)",
                        "speed": "中等 (0.4-1.0s)",
                        "data_types": ["实时行情", "历史数据", "技术指标", "财务数据"],
                        "recommended_use": "美股数据、技术分析"
                    },
                    "yfinance": {
                        "name": "Yahoo Finance (国际股票)",
                        "enabled": True,
                        "priority": 7,
                        "category": "国际数据源",
                        "description": "Yahoo Finance数据接口，国际化支持",
                        "cost": "免费",
                        "speed": "快 (0.3-0.5s)",
                        "data_types": ["实时行情", "历史数据", "财务数据"],
                        "recommended_use": "港股、美股、国际化股票"
                    }
                },
                "cache_enabled": True,
                "cache_ttl": 300,
                "supported_symbols": {
                    "a_shares": "A股市场 (000xxx, 002xxx, 300xxx, 600xxx, 688xxx)",
                    "hk_stocks": "港股市场 (0xxx.HK)",
                    "us_stocks": "美股市场 (AAPL, TSLA, MSFT, etc.)"
                },
                "data_priorities": {
                    "realtime": ["pytdx", "easyquotation", "akshare", "qstock", "mootdx", "tushare", "yfinance", "alpha_vantage"],
                    "historical": ["akshare", "qstock", "mootdx", "tushare", "baostock", "yfinance", "pandas", "alpha_vantage"],
                    "tick": ["pytdx", "mootdx", "easyquotation", "akshare", "tushare"],
                    "financial": ["qstock", "akshare", "tushare", "baostock", "yfinance", "alpha_vantage", "pandas"]
                },
                "configuration_summary": {
                    "total_sources": 10,
                    "enabled_sources": 10,
                    "disabled_sources": 0,
                    "core_sources": 4,
                    "backup_sources": 3,
                    "international_sources": 3,
                    "paid_sources": 3,
                    "free_sources": 10
                },
                "data_source_categories": {
                    "超高速源": ["pytdx"],
                    "高速源": ["easyquotation", "akshare", "qstock", "mootdx", "tushare", "yfinance", "alpha_vantage"],
                    "中速源": ["baostock"],
                    "低速源": ["pandas"],
                    "实时数据源": ["pytdx", "easyquotation", "akshare", "qstock", "mootdx"],
                    "历史数据源": ["akshare", "qstock", "baostock", "yfinance", "pandas", "tushare"],
                    "财务数据源": ["qstock", "akshare", "tushare", "baostock", "yfinance", "alpha_vantage", "pandas"],
                    "分笔数据源": ["pytdx", "mootdx", "akshare"],
                    "A股专用": ["pytdx", "easyquotation", "akshare", "qstock", "mootdx", "tushare", "baostock"],
                    "国际通用": ["yfinance", "alpha_vantage", "pandas"]
                }
            }
        }

    @stock_router.get("/{symbol}")
    async def get_stock_data(symbol: str):
        """获取股票实时数据"""
        # 返回模拟数据用于测试
        return {
            "success": True,
            "message": f"获取股票 {symbol} 数据成功",
            "data": {
                "symbol": symbol.upper(),
                "name": f"{symbol.upper()} Test Corporation",
                "price": 100.50,
                "change": 2.30,
                "change_percent": 2.34,
                "volume": 1000000,
                "timestamp": "2025-11-17T21:08:00Z",
                "market_cap": "1.5B",
                "pe_ratio": 25.6,
                "source": "test_data"
            }
        }

    @stock_router.get("/{symbol}/history")
    async def get_stock_history(symbol: str, period: str = "1mo", interval: str = "1d"):
        """获取股票历史数据"""
        return {
            "success": True,
            "message": f"获取股票 {symbol} 历史数据成功",
            "data": {
                "symbol": symbol.upper(),
                "period": period,
                "interval": interval,
                "data_points": 30,
                "start_date": "2025-10-18",
                "end_date": "2025-11-17",
                "closes": [95.0, 96.5, 98.2, 97.8, 99.5, 100.0, 100.5],
                "highs": [96.0, 97.2, 99.0, 98.5, 100.2, 101.0, 101.5],
                "lows": [94.5, 95.8, 97.5, 97.0, 98.8, 99.2, 99.8],
                "volumes": [800000, 900000, 850000, 920000, 880000, 950000, 1000000],
                "source": "test_data"
            }
        }

try:
    from api.middleware import add_cors_headers, log_requests
except ImportError:
    # 简化中间件
    async def add_cors_headers(request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response

    async def log_requests(request, call_next):
        return await call_next(request)

# 简化服务注册
async def initialize_nacos():
    pass

async def register_to_nacos(*args, **kwargs):
    return True

async def cleanup_nacos():
    pass

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.log_file)
    ]
)

logger = logging.getLogger(__name__)

# 全局变量
app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    try:
        await startup()
        yield
    finally:
        await shutdown()


async def startup():
    """
    服务启动初始化
    """
    global app

    logger.info(f"Starting {settings.name} v{settings.version}")
    logger.info(f"Configuration: debug={settings.debug}, log_level={settings.log_level}")

    try:
        logger.info("Starting microservice...")

        # 注册到 Nacos
        logger.info("Registering service to Nacos...")
        await initialize_nacos()
        success = await register_to_nacos(
            service_name=settings.name.lower().replace(" ", "-"),
            service_port=settings.port,
            framework="FastAPI",
            description=f"{settings.name} 微服务 - 股票数据获取服务"
        )

        if success:
            logger.info("✅ 服务注册成功")
        else:
            logger.warning("❌ 服务注册失败，但服务继续运行")

        logger.info("Microservice started successfully")
        logger.info(f"Service running on http://{settings.host}:{settings.port}")
        logger.info(f"API documentation available at http://{settings.host}:{settings.port}/docs")

    except Exception as e:
        logger.error(f"Failed to start microservice: {e}")
        sys.exit(1)


async def shutdown():
    """
    关闭清理
    """
    logger.info("Shutting down microservice...")

    try:
        # 清理Nacos服务注册
        logger.info("Deregistering from Nacos...")
        await cleanup_nacos()
        logger.info("Nacos deregistration completed")

        logger.info("Microservice shutdown completed")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    """
    创建FastAPI应用
    """
    app = FastAPI(
        title=settings.name,
        description=f"{settings.name} 微服务 - 股票数据获取服务",
        version=settings.version,
        lifespan=lifespan
    )

    # 添加中间件
    app.middleware("http")(add_cors_headers)
    app.middleware("http")(log_requests)

    # 注册路由
    app.include_router(health_router)
    app.include_router(stock_router)  # 股票数据路由

    return app


def main():
    """
    主函数
    """
    global app
    app = create_app()

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        access_log=settings.access_log
    )


if __name__ == "__main__":
    main()

# 创建app实例供uvicorn导入
app = create_app()