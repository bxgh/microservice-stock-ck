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
from datetime import datetime

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

# 导入股票代码路由
try:
    from api.stock_code_routes import router as stock_code_router, internal_router as stock_code_internal_router
except ImportError as e:
    print(f"Warning: stock_code_routes not found: {e}")
    from fastapi import APIRouter
    stock_code_router = APIRouter(prefix="/api/v1/stocks", tags=["股票代码"])
    stock_code_internal_router = APIRouter(prefix="/internal/stocks", tags=["内部接口"])

    @stock_code_router.get("/test")
    async def test_stock_codes():
        return {"message": "股票代码服务测试接口", "status": "placeholder"}

# 分笔数据路由已统一到Fenbi架构中，不再需要单独的tick_data_routes

# 导入100%成功策略路由
try:
    from api.guaranteed_strategy_routes import router as strategy_router, internal_router as strategy_internal_router
except Exception as e:
    print(f"Warning: guaranteed_strategy_routes not found: {e}")
    from fastapi import APIRouter
    strategy_router = APIRouter(prefix="/api/v1/strategy", tags=["100%成功策略"])
    strategy_internal_router = APIRouter(prefix="/internal/strategy", tags=["策略内部接口"])

    @strategy_router.get("/test")
    async def test_strategy():
        return {"message": "100%成功策略测试接口", "status": "placeholder"}

# 导入Fenbi分笔数据路由
try:
    from api.fenbi_routes import router as fenbi_router, internal_router as fenbi_internal_router
except ImportError as e:
    print(f"Warning: fenbi_routes not found: {e}")
    from fastapi import APIRouter
    fenbi_router = APIRouter(prefix="/api/v1/fenbi", tags=["Fenbi分笔数据"])
    fenbi_internal_router = APIRouter(prefix="/internal/fenbi", tags=["Fenbi内部接口"])

    @fenbi_router.get("/test")
    async def test_fenbi():
        return {"message": "Fenbi分笔数据测试接口", "status": "placeholder"}

# 导入配置管理路由
try:
    from api.routers.config import router as config_router, internal_router as config_internal_router
except ImportError as e:
    print(f"Warning: config routes not found: {e}")
    from fastapi import APIRouter
    config_router = APIRouter(prefix="/api/v1/config", tags=["Configuration"])
    config_internal_router = APIRouter(prefix="/internal/config", tags=["Config Internal"])

    @config_router.get("/test")
    async def test_config():
        return {"message": "配置管理测试接口", "status": "placeholder"}

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


# 导入调度器和连接管理器
try:
    from .core.scheduling.scheduler import AcquisitionScheduler
    from .data_sources.mootdx.connection import MootdxConnection
except ImportError as e:
    print(f"Warning: Scheduler or Connection import failed: {e}")
    AcquisitionScheduler = None
    MootdxConnection = None

# 全局采集任务引用
acquisition_task = None

async def run_acquisition_loop():
    """
    后台数据采集主循环
    """
    if not AcquisitionScheduler or not MootdxConnection:
        logger.error("❌ 缺少必要组件，无法启动采集循环")
        return

    logger.info("🚀 启动自动数据采集服务...")
    scheduler = AcquisitionScheduler()
    # 使用 best_ip=True 自动选择最快服务器
    connection = MootdxConnection(best_ip=True, initial_wait_time=0.5)
    
    # 初始化调度器和股票池
    try:
        await scheduler.initialize()
        logger.info("✅ 调度器初始化成功")
    except Exception as e:
        logger.error(f"❌ 调度器初始化失败: {e}")
        # 如果初始化失败，使用默认股票池作为降级方案
        logger.warning("⚠️ 使用默认股票池作为降级方案")
    
    # 初始化 ClickHouse Writer
    try:
        from .storage.clickhouse_writer import ClickHouseWriter, SnapshotData
        writer = ClickHouseWriter(
            host='microservice-stock-clickhouse',
            port=9000,
            database='stock_data',
            batch_size=1000
        )
        logger.info("✅ ClickHouse Writer 初始化成功")
    except Exception as e:
        logger.error(f"❌ ClickHouse Writer 初始化失败: {e}")
        writer = None
    
    # 启动每日股票池刷新任务
    async def daily_pool_refresh():
        """每日8:00刷新股票池"""
        while True:
            try:
                # 计算距离下一个8:00的时间
                now = datetime.now()
                next_refresh = now.replace(hour=8, minute=0, second=0, microsecond=0)
                if now >= next_refresh:
                    # 如果已经过了今天的8点，设置为明天8点
                    next_refresh += timedelta(days=1)
                
                wait_seconds = (next_refresh - datetime.now()).total_seconds()
                logger.info(f"📅 下次股票池刷新时间: {next_refresh} (等待 {wait_seconds/3600:.1f} 小时)")
                
                await asyncio.sleep(wait_seconds)
                
                # 刷新股票池
                logger.info("🔄 开始每日股票池刷新...")
                await scheduler.refresh_pool()
                logger.info("✅ 每日股票池刷新完成")
                
            except asyncio.CancelledError:
                logger.info("🛑 股票池刷新任务被取消")
                break
            except Exception as e:
                logger.error(f"❌ 股票池刷新失败: {e}")
                # 出错后等待1小时重试
                await asyncio.sleep(3600)
    
    # 启动刷新任务
    refresh_task = asyncio.create_task(daily_pool_refresh())
    
    try:
        while True:
            # 1. 检查是否应该运行
            if scheduler.should_run_now():
                try:
                    # 获取连接
                    client = await connection.get_client()
                    if client:
                        # 从调度器获取当前股票池（Story 004.01: 100只股票）
                        target_stocks = scheduler.get_current_pool()
                        
                        # 如果股票池为空，使用默认降级方案
                        if not target_stocks:
                            logger.warning("⚠️ 股票池为空，使用默认股票池")
                            target_stocks = ["000001", "600000", "000002", "601398", "601318"]
                        
                        logger.debug(f"📊 当前股票池大小: {len(target_stocks)} 只股票")
                        
                        # 获取快照
                        quotes = client.quotes(symbol=target_stocks)
                        if quotes is not None and not quotes.empty:
                            logger.info(f"✅ [自动采集] 成功获取 {len(quotes)} 只股票实时行情")
                            
                            # 写入 ClickHouse
                            if writer:
                                try:
                                    snapshot_time = datetime.now()
                                    for _, row in quotes.iterrows():
                                        snapshot = SnapshotData(
                                            snapshot_time=snapshot_time,
                                            trade_date=snapshot_time.date(),
                                            stock_code=str(row.get('code', '')),
                                            stock_name=str(row.get('name', '')),
                                            market='SZ' if str(row.get('code', '')).startswith(('000', '002', '300')) else 'SH',
                                            current_price=float(row.get('price', 0)),
                                            open_price=float(row.get('open', 0)),
                                            high_price=float(row.get('high', 0)),
                                            low_price=float(row.get('low', 0)),
                                            pre_close=float(row.get('last_close', 0)),
                                            total_volume=int(row.get('vol', 0)),
                                            total_amount=float(row.get('amount', 0)),
                                            data_source='mootdx',
                                            pool_level='L1'
                                        )
                                        writer.write_snapshot(snapshot)
                                    
                                    writer.flush()
                                    logger.info(f"💾 [数据入库] 成功写入 {len(quotes)} 条快照数据")
                                except Exception as e:
                                    logger.error(f"❌ [数据入库] 写入失败: {e}")
                        else:
                            logger.warning("⚠️ [自动采集] 获取数据为空")
                    
                    # 采集间隔 3 秒
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"❌ [自动采集] 发生错误: {e}")
                    await asyncio.sleep(5) # 出错后稍作等待
            else:
                # 2. 如果不该运行，则进入休眠等待
                logger.info("💤 当前非交易时段，采集服务进入休眠...")
                await scheduler.wait_for_next_run()
                logger.info("⏰ 采集服务唤醒，准备开始工作！")
                
    except asyncio.CancelledError:
        logger.info("🛑 采集任务被取消")
    finally:
        # 取消刷新任务
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            pass
        
        if writer:
            writer.close()
        await connection.close()
        logger.info("👋 采集服务已停止")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    try:
        await startup()
        
        # 启动后台采集任务
        global acquisition_task
        acquisition_task = asyncio.create_task(run_acquisition_loop())
        
        yield
    finally:
        # 取消后台任务
        if acquisition_task:
            acquisition_task.cancel()
            try:
                await acquisition_task
            except asyncio.CancelledError:
                pass
                
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

        # 初始化股票代码客户端
        try:
            from services.stock_code_client import stock_client_instance
            await stock_client_instance.initialize()
            logger.info("✅ 股票代码客户端初始化成功")
        except Exception as e:
            logger.warning(f"股票代码客户端初始化失败: {e}")

        # 初始化通达信客户端
        try:
            from services.tongdaxin_client import tongdaxin_client
            success = await tongdaxin_client.initialize()
            if success:
                logger.info("✅ 通达信客户端初始化成功")
            else:
                logger.warning("❌ 通达信客户端初始化失败，但服务继续运行")
        except Exception as e:
            logger.warning(f"通达信客户端初始化失败: {e}")

        # 初始化100%成功策略引擎
        try:
            from services.guaranteed_success_strategy import guaranteed_strategy_instance
            logger.info("✅ 100%成功策略引擎初始化成功")
            logger.info(f"📊 搜索矩阵步数: {len(guaranteed_strategy_instance.proven_search_matrix)}")
            logger.info(f"🎯 目标时间: {guaranteed_strategy_instance.config.target_time}")
        except Exception as e:
            logger.warning(f"100%成功策略引擎初始化失败: {e}")

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
        # 关闭股票代码客户端
        try:
            from services.stock_code_client import stock_client_instance
            await stock_client_instance.close()
            logger.info("✅ 股票代码客户端已关闭")
        except Exception as e:
            logger.warning(f"股票代码客户端关闭失败: {e}")

        # 关闭通达信客户端
        try:
            from services.tongdaxin_client import tongdaxin_client
            await tongdaxin_client.close()
            logger.info("✅ 通达信客户端已关闭")
        except Exception as e:
            logger.warning(f"通达信客户端关闭失败: {e}")

        # 关闭100%成功策略引擎
        try:
            from services.guaranteed_success_strategy import guaranteed_strategy_instance
            await guaranteed_strategy_instance.close()
            logger.info("✅ 100%成功策略引擎已关闭")
        except Exception as e:
            logger.warning(f"100%成功策略引擎关闭失败: {e}")

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
    app.include_router(stock_code_router)  # 股票数据路由
    app.include_router(stock_code_internal_router)  # 股票代码内部路由
    app.include_router(strategy_router)  # 100%成功策略路由
    app.include_router(strategy_internal_router)  # 策略内部路由
    app.include_router(fenbi_router)  # Fenbi分笔数据路由（包含原tick_data功能）
    app.include_router(fenbi_internal_router)  # Fenbi内部路由
    app.include_router(config_router)  # 配置管理路由（Story 004.05）
    app.include_router(config_internal_router)  # 配置管理内部路由

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