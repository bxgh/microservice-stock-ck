from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from core.dq import DQReport, DQFinding
from core.dq_inspector_service import DQInspectorService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
inspector = DQInspectorService()

@router.post("/run", summary="手动触发全量巡检")
async def run_inspection(date: Optional[str] = Query(None, description="巡检目标日期 (YYYY-MM-DD), 默认为昨日")):
    """
    手动启动数据质量巡检任务
    """
    try:
        result = await inspector.run_full_inspection(date)
        return result
    except Exception as e:
        logger.error(f"手动巡检失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports", response_model=List[Dict[str, Any]], summary="获取巡检报告列表")
async def get_reports(limit: int = 10):
    """
    从数据库获取最近的巡检报告汇总
    """
    import aiomysql
    from config.settings import settings
    
    config = {
        "host": settings.MYSQL_HOST,
        "port": settings.MYSQL_PORT,
        "user": settings.MYSQL_USER,
        "password": settings.MYSQL_PASSWORD,
        "db": settings.MYSQL_DATABASE,
        "autocommit": True
    }
    
    try:
        conn = await aiomysql.connect(**config)
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM dq_reports ORDER BY inspection_date DESC LIMIT %s", (limit,))
            reports = await cur.fetchall()
        conn.close()
        return reports
    except Exception as e:
        logger.error(f"获取报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/findings", response_model=List[Dict[str, Any]], summary="获取异常详情")
async def get_findings(date: str, rule_id: Optional[str] = None):
    """
    获取指定日期的异常发现详情
    """
    import aiomysql
    from config.settings import settings
    
    config = {
        "host": settings.MYSQL_HOST,
        "port": settings.MYSQL_PORT,
        "user": settings.MYSQL_USER,
        "password": settings.MYSQL_PASSWORD,
        "db": settings.MYSQL_DATABASE,
        "autocommit": True
    }
    
    try:
        conn = await aiomysql.connect(**config)
        async with conn.cursor(aiomysql.DictCursor) as cur:
            sql = "SELECT * FROM dq_findings WHERE trade_date = %s"
            params = [date]
            if rule_id:
                sql += " AND rule_id = %s"
                params.append(rule_id)
            
            await cur.execute(sql, tuple(params))
            findings = await cur.fetchall()
        conn.close()
        return findings
    except Exception as e:
        logger.error(f"获取异常详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
