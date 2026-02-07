"""
扫描任务 API 路由

提供每日扫描触发、状态查询和结果获取接口。
"""
import logging
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from scanner import ScannerConfig, ScannerEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scan", tags=["Scan"])

# 全局扫描引擎实例
_scanner_engine: ScannerEngine | None = None


def get_scanner_engine(request: Request) -> ScannerEngine:
    """获取扫描引擎实例"""
    global _scanner_engine
    if _scanner_engine is None:
        # 从 app.state 获取 strategy_registry
        strategy_registry = getattr(request.app.state, 'strategy_registry', None)
        _scanner_engine = ScannerEngine(
            config=ScannerConfig(),
            strategy_registry=strategy_registry
        )
    return _scanner_engine


class DailyScanRequest(BaseModel):
    """每日扫描请求"""
    scan_date: date | None = None
    strategies: list[str] | None = None
    force: bool = False


class DailyScanResponse(BaseModel):
    """每日扫描响应"""
    success: bool
    message: str
    data: dict[str, Any] | None = None


@router.post("/daily", response_model=DailyScanResponse)
async def trigger_daily_scan(
    request: DailyScanRequest,
    engine: ScannerEngine = Depends(get_scanner_engine)
):
    """
    触发每日扫描

    异步执行，立即返回任务ID。
    """
    try:
        # 获取股票池 (暂时使用硬编码的测试数据)
        # TODO: 从 UniversePoolService 获取
        stock_codes = ["600519", "000001", "300750"]  # 测试数据

        scan_date = request.scan_date or date.today()

        job = await engine.run_daily_scan(
            stock_codes=stock_codes,
            scan_date=scan_date,
            strategies=request.strategies
        )

        return DailyScanResponse(
            success=True,
            message="扫描任务已完成",
            data=job.to_dict()
        )

    except Exception as e:
        logger.error(f"Daily scan failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    engine: ScannerEngine = Depends(get_scanner_engine)
):
    """查询扫描任务状态"""
    job = engine.get_current_job()

    if job is None or str(job.job_id) != job_id:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "success": True,
        "data": job.to_dict()
    }


@router.get("/results/latest")
async def get_latest_results(
    strategy: str | None = Query(None, description="筛选特定策略"),
    min_score: float | None = Query(None, description="最低得分"),
    limit: int = Query(20, description="返回数量"),
    engine: ScannerEngine = Depends(get_scanner_engine)
):
    """获取最新扫描结果"""
    results = engine.get_results()

    # 过滤
    if strategy:
        results = [r for r in results if r.get("strategy_id") == strategy]

    if min_score is not None:
        results = [r for r in results if r.get("score", 0) >= min_score]

    # 排序 (按得分降序)
    results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)

    # 限制数量
    results = results[:limit]

    job = engine.get_current_job()

    return {
        "success": True,
        "data": {
            "scan_date": job.scan_date.isoformat() if job else None,
            "job_id": str(job.job_id) if job else None,
            "total_matches": len(results),
            "results": results
        }
    }


@router.get("/errors")
async def get_scan_errors(
    engine: ScannerEngine = Depends(get_scanner_engine)
):
    """获取扫描错误列表"""
    errors = engine.get_errors()

    return {
        "success": True,
        "data": {
            "total_errors": len(errors),
            "errors": errors
        }
    }
