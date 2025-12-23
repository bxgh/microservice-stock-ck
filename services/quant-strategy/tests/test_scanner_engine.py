import sys
import pytest
import asyncio
from datetime import date

# Add src to path for imports to work correctly in Docker if needed
sys.path.insert(0, '/app/src')

from scanner.engine import ScannerEngine, ScannerConfig
from strategies.registry import StrategyRegistry
from strategies.value_strategy import ValueStrategy
from database import init_database
from database.session import create_session
from database.scan_models import ScanJobModel, StrategyMatchModel
from sqlalchemy import select

# Setup helper
_db_initialized = False

async def ensure_db_initialized():
    global _db_initialized
    if not _db_initialized:
        await init_database()
        _db_initialized = True
    
    # 清理相关表以避免 IntegrityError
    from database.scan_models import ScanJobModel, StrategyMatchModel, ScanErrorModel
    from sqlalchemy import delete
    session = create_session()
    try:
        await session.execute(delete(ScanErrorModel))
        await session.execute(delete(StrategyMatchModel))
        await session.execute(delete(ScanJobModel))
        await session.commit()
    finally:
        await session.close()

@pytest.mark.asyncio
async def test_scanner_engine_full_workflow():
    """测试扫描引擎完整工作流（含数据库持久化）"""
    await ensure_db_initialized()
    
    # 1. 初始化注册表和策略
    registry = StrategyRegistry()
    await registry.stop_all()
    
    strategy = ValueStrategy()
    await registry.register(strategy.strategy_id, strategy)
    
    # 2. 初始化引擎
    engine = ScannerEngine(
        config=ScannerConfig(chunk_size=2),
        strategy_registry=registry
    )
    
    # 3. 运行扫描 (默认 persist=True)
    stock_codes = ["600519", "000001", "300750", "601318"]
    job = await engine.run_daily_scan(stock_codes=stock_codes)
    
    # 4. 验证内存结果
    assert job.status.value == "success"
    assert job.total_stocks == 4
    assert job.processed_stocks == 4
    
    # 5. 验证数据库持久化
    session = create_session()
    try:
        # 验证 Job
        stmt = select(ScanJobModel).where(ScanJobModel.job_id == str(job.job_id))
        res = await session.execute(stmt)
        db_job = res.scalar()
        assert db_job is not None
        assert db_job.status == "success"
        assert db_job.total_stocks == 4
        
        # 验证 Matches
        stmt = select(StrategyMatchModel).where(StrategyMatchModel.scan_job_id == db_job.id)
        res = await session.execute(stmt)
        db_matches = res.scalars().all()
        assert len(db_matches) == 4
        for m in db_matches:
            assert m.strategy_id == "value"
            assert m.stock_code in stock_codes
    finally:
        await session.close()

@pytest.mark.asyncio
async def test_scanner_engine_partial_failure():
    """测试扫描引擎部分失败（持久化异常记录）"""
    await ensure_db_initialized()
    
    registry = StrategyRegistry()
    await registry.stop_all()
    
    # 一个会抛出异常的模拟策略
    class BuggyStrategy(ValueStrategy):
        @property
        def strategy_id(self) -> str:
            return "buggy"
        async def evaluate(self, code, data):
            if code == "FAIL":
                raise ValueError("Simulated error")
            return await super().evaluate(code, data)
            
    strategy = BuggyStrategy()
    await registry.register(strategy.strategy_id, strategy)
    
    engine = ScannerEngine(strategy_registry=registry)
    
    stock_codes = ["600519", "FAIL"]
    job = await engine.run_daily_scan(stock_codes=stock_codes)
    
    # 验证状态为 partial
    assert job.status.value == "partial"
    
    # 验证数据库中记录了错误
    from database.scan_models import ScanErrorModel
    session = create_session()
    try:
        stmt = select(ScanErrorModel).join(ScanJobModel).where(ScanJobModel.job_id == str(job.job_id))
        res = await session.execute(stmt)
        db_errors = res.scalars().all()
        assert len(db_errors) == 1
        assert db_errors[0].stock_code == "FAIL"
        assert "Simulated error" in db_errors[0].error_message
    finally:
        await session.close()
