"""
扫描引擎模块

负责批量处理股票池，调用所有注册策略进行评估。
采用分块向量化处理，支持故障隔离。
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class ScanJobStatus(Enum):
    """扫描任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"  # 部分完成
    FAILED = "failed"


@dataclass
class ScanJob:
    """扫描任务"""
    job_id: UUID
    scan_date: date
    status: ScanJobStatus
    total_stocks: int = 0
    processed_stocks: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None
    
    @property
    def progress_percent(self) -> float:
        if self.total_stocks == 0:
            return 0.0
        return (self.processed_stocks / self.total_stocks) * 100
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": str(self.job_id),
            "scan_date": self.scan_date.isoformat(),
            "status": self.status.value,
            "total_stocks": self.total_stocks,
            "processed_stocks": self.processed_stocks,
            "progress_percent": self.progress_percent,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error_message": self.error_message
        }


@dataclass
class ScannerConfig:
    """扫描器配置"""
    chunk_size: int = 200  # 每批处理股票数
    max_concurrent_strategies: int = 5  # 并发策略数
    timeout_seconds: int = 3600  # 最大运行时间 (60分钟)
    fail_fast: bool = False  # 是否遇错即停


class ScannerEngine:
    """
    扫描引擎
    
    负责遍历股票池，调用所有策略进行评估。
    采用分块处理，支持故障隔离和进度追踪。
    """
    
    def __init__(
        self,
        config: ScannerConfig | None = None,
        strategy_registry=None,
        data_prefetcher=None
    ):
        """
        初始化扫描引擎
        
        Args:
            config: 扫描器配置
            strategy_registry: 策略注册中心
            data_prefetcher: 数据预取器
        """
        self.config = config or ScannerConfig()
        self._registry = strategy_registry
        self._prefetcher = data_prefetcher
        self._current_job: ScanJob | None = None
        self._results: list[dict] = []
        self._errors: list[dict] = []
        logger.info(f"ScannerEngine initialized with chunk_size={self.config.chunk_size}")
    
    async def run_daily_scan(
        self,
        stock_codes: list[str],
        scan_date: date | None = None,
        strategies: list[str] | None = None,
        persist: bool = True  # 是否保存到数据库
    ) -> ScanJob:
        """
        执行每日扫描
        
        Args:
            stock_codes: 待扫描股票代码列表
            scan_date: 扫描日期，默认今天
            strategies: 指定策略ID列表，默认全部
            persist: 是否持久化到数据库
            
        Returns:
            ScanJob: 扫描任务对象
        """
        scan_date = scan_date or date.today()
        
        # 创建任务
        self._current_job = ScanJob(
            job_id=uuid4(),
            scan_date=scan_date,
            status=ScanJobStatus.PENDING,
            total_stocks=len(stock_codes),
            processed_stocks=0
        )
        
        self._results = []
        self._errors = []
        
        logger.info(
            f"Starting daily scan: job_id={self._current_job.job_id}, "
            f"date={scan_date}, stocks={len(stock_codes)}"
        )
        
        try:
            self._current_job.status = ScanJobStatus.RUNNING
            self._current_job.started_at = datetime.now()
            
            # 1. 初始持久化任务状态
            if persist:
                await self._db_save_job_status()
            
            # 获取策略列表
            active_strategies = self._get_active_strategies(strategies)
            if not active_strategies:
                raise ValueError("No active strategies found")
            
            logger.info(f"Active strategies: {[s.strategy_id for s in active_strategies]}")
            
            # 分块处理
            chunks = self._create_chunks(stock_codes)
            total_chunks = len(chunks)
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{total_chunks} ({len(chunk)} stocks)")
                await self._process_chunk(chunk, active_strategies)
                self._current_job.processed_stocks += len(chunk)
                
                # 每块处理完更新一次进度
                if persist:
                    await self._db_save_job_status()
            
            # 完成
            self._current_job.finished_at = datetime.now()
            
            if self._errors:
                self._current_job.status = ScanJobStatus.PARTIAL
                self._current_job.error_message = f"{len(self._errors)} errors occurred"
            else:
                self._current_job.status = ScanJobStatus.SUCCESS
            
            # 2. 持久化最终结果和任务状态
            if persist:
                await self._db_save_results()
                await self._db_save_job_status()
            
            duration = (self._current_job.finished_at - self._current_job.started_at).total_seconds()
            logger.info(
                f"Scan completed: status={self._current_job.status.value}, "
                f"duration={duration:.1f}s, results={len(self._results)}, errors={len(self._errors)}"
            )
            
        except Exception as e:
            logger.error(f"Scan failed: {e}", exc_info=True)
            self._current_job.status = ScanJobStatus.FAILED
            self._current_job.error_message = str(e)
            self._current_job.finished_at = datetime.now()
            if persist:
                await self._db_save_job_status()
        
        return self._current_job

    async def _db_save_job_status(self):
        """保存任务状态到数据库"""
        from database.session import create_session
        from database.scan_models import ScanJobModel
        from sqlalchemy import select
        
        session = create_session()
        try:
            # 查找现有任务
            stmt = select(ScanJobModel).where(ScanJobModel.job_id == str(self._current_job.job_id))
            result = await session.execute(stmt)
            db_job = result.scalar_one_or_none()
            
            if db_job:
                db_job.status = self._current_job.status.value
                db_job.processed_stocks = self._current_job.processed_stocks
                db_job.started_at = self._current_job.started_at
                db_job.finished_at = self._current_job.finished_at
                db_job.error_message = self._current_job.error_message
            else:
                db_job = ScanJobModel(
                    job_id=str(self._current_job.job_id),
                    scan_date=self._current_job.scan_date,
                    status=self._current_job.status.value,
                    total_stocks=self._current_job.total_stocks,
                    processed_stocks=self._current_job.processed_stocks,
                    started_at=self._current_job.started_at
                )
                session.add(db_job)
            
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Error saving job status: {e}")
            raise
        finally:
            await session.close()

    async def _db_save_results(self):
        """保存扫描结果到数据库"""
        from database.session import create_session
        from database.scan_models import ScanJobModel, StrategyMatchModel, ScanErrorModel
        from sqlalchemy import select
        import json
        
        session = create_session()
        try:
            # 1. 获取内部 ID
            stmt = select(ScanJobModel.id).where(ScanJobModel.job_id == str(self._current_job.job_id))
            result = await session.execute(stmt)
            internal_id = result.scalar()
            
            if not internal_id:
                logger.error(f"Cannot save results: job_id {self._current_job.job_id} not found")
                return
            
            # 2. 批量保存成功结果
            for res in self._results:
                match = StrategyMatchModel(
                    scan_job_id=internal_id,
                    scan_date=self._current_job.scan_date,
                    stock_code=res["stock_code"],
                    strategy_id=res["strategy_id"],
                    score=res["score"],
                    passed=res["passed"],
                    reason=res["reason"],
                    details=json.dumps(res.get("details", {}))
                )
                session.add(match)
            
            # 3. 批量保存错误信息
            for err in self._errors:
                error_record = ScanErrorModel(
                    scan_job_id=internal_id,
                    stock_code=err["stock_code"],
                    strategy_id=err.get("strategy_id"),
                    error_message=err["error"]
                )
                session.add(error_record)
            
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Error saving scan results: {e}")
            raise
        finally:
            await session.close()
    
    def _get_active_strategies(self, strategy_ids: list[str] | None = None) -> list:
        """获取活跃策略列表"""
        if self._registry is None:
            logger.warning("No strategy registry configured, returning empty list")
            return []
        
        all_strategies = []
        for sid in self._registry.list_all():
            strategy = self._registry.get(sid)
            if strategy and strategy.is_initialized():
                if strategy_ids is None or strategy.strategy_id in strategy_ids:
                    all_strategies.append(strategy)
        
        return all_strategies
    
    def _create_chunks(self, stock_codes: list[str]) -> list[list[str]]:
        """将股票列表分块"""
        chunk_size = self.config.chunk_size
        return [
            stock_codes[i:i + chunk_size]
            for i in range(0, len(stock_codes), chunk_size)
        ]
    
    async def _process_chunk(self, codes: list[str], strategies: list) -> None:
        """处理单个块"""
        # 预取数据
        data_map = await self._prefetch_data(codes)
        
        # 对每只股票应用所有策略
        for code in codes:
            stock_data = data_map.get(code, {})
            await self._evaluate_stock(code, stock_data, strategies)
    
    async def _prefetch_data(self, codes: list[str]) -> dict[str, dict]:
        """预取数据"""
        if self._prefetcher is None:
            logger.warning("No data prefetcher configured, returning empty data")
            return {code: {} for code in codes}
        
        try:
            return await self._prefetcher.fetch_batch(codes)
        except Exception as e:
            logger.error(f"Data prefetch failed: {e}")
            return {code: {} for code in codes}
    
    async def _evaluate_stock(
        self,
        code: str,
        data: dict[str, Any],
        strategies: list
    ) -> None:
        """评估单只股票"""
        for strategy in strategies:
            try:
                result = await asyncio.wait_for(
                    strategy.evaluate(code, data),
                    timeout=10.0  # 单个评估超时 10 秒
                )
                self._results.append(result.to_dict())
                
            except asyncio.TimeoutError:
                self._record_error(code, strategy.strategy_id, "Evaluation timeout")
            except Exception as e:
                self._record_error(code, strategy.strategy_id, str(e))
    
    def _record_error(self, code: str, strategy_id: str, message: str) -> None:
        """记录错误"""
        self._errors.append({
            "stock_code": code,
            "strategy_id": strategy_id,
            "error": message,
            "timestamp": datetime.now().isoformat()
        })
        logger.warning(f"Evaluation error: {code}/{strategy_id} - {message}")
    
    def get_results(self) -> list[dict]:
        """获取扫描结果"""
        return self._results
    
    def get_errors(self) -> list[dict]:
        """获取错误列表"""
        return self._errors
    
    def get_current_job(self) -> ScanJob | None:
        """获取当前任务"""
        return self._current_job
