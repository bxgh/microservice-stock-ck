"""
数据质量检查 API 路由
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from typing import Optional
import logging

from core.data_quality_service import DataQualityService

router = APIRouter(prefix="/api/v1/quality", tags=["data-quality"])
logger = logging.getLogger(__name__)


# ========== 依赖注入：服务实例管理 ==========
async def get_data_quality_service():
    """
    FastAPI 依赖注入：创建并管理 DataQualityService 实例
    
    优势：
    - 避免每次请求都创建/销毁连接池
    - 自动处理资源清理
    """
    service = DataQualityService()
    await service.initialize()
    try:
        yield service
    finally:
        await service.close()


@router.get("/timeliness")
async def check_timeliness(service: DataQualityService = Depends(get_data_quality_service)):
    """
    检查数据时效性
    
    返回最新数据日期和滞后天数
    """
    try:
        return await service.check_timeliness()
    except Exception as e:
        logger.error(f"时效性检查失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consistency")
async def check_consistency(
    days: int = Query(7, description="检查最近 N 天的对账情况"),
    service: DataQualityService = Depends(get_data_quality_service)
):
    """
    检查 MySQL 与 ClickHouse 数据一致性 (对账)
    
    对比源头数据库与副本数据库的记录总数
    """
    try:
        return await service.check_cross_db_consistency(days)
    except Exception as e:
        logger.error(f"对账检查失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/duplicates")
async def check_duplicates(
    days: int = Query(7, description="检查最近 N 天"),
    service: DataQualityService = Depends(get_data_quality_service)
):
    """
    检查重复数据
    """
    try:
        return await service.check_duplicates(days)
    except Exception as e:
        logger.error(f"重复数据检查失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend")
async def check_trend_stability(
    weeks: int = Query(4, description="检查最近 N 周"),
    service: DataQualityService = Depends(get_data_quality_service)
):
    """
    检查数据量趋势稳定性
    """
    try:
        return await service.check_trend_stability(weeks)
    except Exception as e:
        logger.error(f"趋势检查失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/{stock_code}")
async def check_stock_quality(
    stock_code: str,
    service: DataQualityService = Depends(get_data_quality_service)
):
    """
    检查单只股票的数据质量
    
    返回完整性、连续性和健康度评分
    """
    try:
        completeness = await service.check_stock_completeness(stock_code)
        continuity = await service.check_stock_continuity(stock_code)
        health = await service.calculate_health_score(stock_code)
        
        return {
            "stock_code": stock_code,
            "health_score": health.get("health_score"),
            "completeness": completeness,
            "continuity": continuity,
            "summary": health
        }
    except Exception as e:
        logger.error(f"个股质量检查失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/daily")
async def get_daily_report(service: DataQualityService = Depends(get_data_quality_service)):
    """
    生成每日质量报告
    """
    try:
        return await service.run_daily_check()
    except Exception as e:
        logger.error(f"生成每日报告失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/weekly")
async def get_weekly_report(service: DataQualityService = Depends(get_data_quality_service)):
    """
    生成每周质量报告
    """
    try:
        return await service.run_weekly_check()
    except Exception as e:
        logger.error(f"生成每周报告失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scan/ledger")
async def get_scan_ledger(
    status: Optional[str] = Query(None, description="状态过滤: OK, ERROR"),
    limit: int = Query(100, ge=1, le=1000),
    service: DataQualityService = Depends(get_data_quality_service)
):
    """
    查询全市场深度扫描结果 (Ledger)
    """
    try:
        from data_access.mysql_pool import MySQLPoolManager
        pool = await MySQLPoolManager.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = "SELECT * FROM stock_health_ledger"
                params = []
                if status:
                    sql += " WHERE status = %s"
                    params.append(status)
                sql += " ORDER BY last_scan_time DESC LIMIT %s"
                params.append(limit)
                
                await cursor.execute(sql, tuple(params))
                columns = [col[0] for col in cursor.description]
                results = []
                for row in await cursor.fetchall():
                    results.append(dict(zip(columns, row)))
        return results
    except Exception as e:
        logger.error(f"获取扫描台账失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _run_quality_check_task(check_type: str, **kwargs):
    """后台质量检查任务"""
    service = DataQualityService()
    try:
        await service.initialize()
        
        if check_type == "daily":
            report = await service.run_daily_check()
        elif check_type == "weekly":
            report = await service.run_weekly_check()
        elif check_type == "universe":
            batch_size = kwargs.get("batch_size", 100)
            report = await service.run_universe_scan_batch(batch_size=batch_size)
        else:
            logger.error(f"Unknown check_type: {check_type}")
            return
        
        # 发送告警
        if isinstance(report, dict) and report.get("overall_status") in ["WARNING", "ERROR"]:
            logger.warning(f"质量检查发现问题: {report}")
            
        logger.info(f"质量检查后台任务完成: {check_type}")
    except Exception as e:
        logger.error(f"后台质量检查失败: {e}", exc_info=True)
    finally:
        await service.close()


@router.post("/run")
async def trigger_quality_check(
    background_tasks: BackgroundTasks,
    check_type: str = Query("daily", description="检查类型: daily, weekly, universe"),
    batch_size: int = Query(100, description="批次大小 (仅对于 universe 有效)")
):
    """
    手动触发质量检查（后台执行）
    """
    valid_types = ["daily", "weekly", "universe"]
    if check_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"check_type 必须是 {valid_types} 之一")
    
    background_tasks.add_task(_run_quality_check_task, check_type, batch_size=batch_size)
    
    return {
        "status": "accepted",
        "message": f"{check_type} 质量检查已在后台启动",
        "check_report_url": f"/api/v1/quality/report/{check_type}" if check_type != "universe" else "/api/v1/quality/scan/ledger"
    }
