from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

class RecalcSignal(BaseModel):
    id: int
    ts_code: str
    start_date: str
    end_date: str
    request_id: str
    created_at: str

class AckRequest(BaseModel):
    request_id: str
    status: str
    notes: Optional[str] = None

@router.get("/recalc-signals/pending", response_model=Dict[str, Any])
async def get_pending_signals(limit: int = Query(50, ge=1, le=200)):
    """
    获取待处理的重算信号，并自动标记为 PROCESSING (原子锁定)
    """
    from main import mysql_pool
    if not mysql_pool:
        raise HTTPException(status_code=500, detail="MySQL pool not initialized")

    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    # 开启事务
                    await conn.begin()
                    
                    # 1. 查找待处理任务并锁定 (MySQL 8.0 SKIP LOCKED 防止并发冲突)
                    query_select = """
                        SELECT id FROM recalc_signals 
                        WHERE status = 'PENDING' 
                        ORDER BY id ASC 
                        LIMIT %s 
                        FOR UPDATE SKIP LOCKED
                    """
                    await cur.execute(query_select, (limit,))
                    rows = await cur.fetchall()
                    
                    if not rows:
                        await conn.rollback()
                        return {"count": 0, "data": []}
                    
                    ids = [row[0] for row in rows]
                    
                    # 2. 批量更新状态
                    query_update = """
                        UPDATE recalc_signals 
                        SET status = 'PROCESSING', executed_at = NOW() 
                        WHERE id IN ({})
                    """.format(','.join(['%s'] * len(ids)))
                    await cur.execute(query_update, tuple(ids))
                    
                    # 3. 获取完整数据返回
                    query_fetch = """
                        SELECT id, ts_code, start_date, end_date, request_id, created_at 
                        FROM recalc_signals 
                        WHERE id IN ({})
                    """.format(','.join(['%s'] * len(ids)))
                    await cur.execute(query_fetch, tuple(ids))
                    data_rows = await cur.fetchall()
                    
                    await conn.commit()
                    
                    result = []
                    for r in data_rows:
                        result.append({
                            "id": r[0],
                            "ts_code": r[1],
                            "start_date": str(r[2]),
                            "end_date": str(r[3]),
                            "request_id": r[4],
                            "created_at": str(r[5])
                        })
                    
                    return {"count": len(result), "data": result}
                except Exception as inner_e:
                    await conn.rollback()
                    raise inner_e
                
    except Exception as e:
        logger.error(f"Failed to fetch pending signals: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/recalc-signals/ack")
async def acknowledge_signal(req: AckRequest):
    """
    确认信号处理结果，并集成故障告警
    """
    from main import mysql_pool
    from core.notifier import notifier
    if not mysql_pool:
        raise HTTPException(status_code=500, detail="MySQL pool not initialized")

    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    # 1. 尝试执行原子更新 (不再先 SELECT 以防止幻读)
                    await cur.execute(
                        "UPDATE recalc_signals SET status = %s, notes = %s WHERE request_id = %s",
                        (req.status, req.notes, req.request_id)
                    )
                    affected = cur.rowcount
                    
                    if affected == 0:
                        # 检查是否是因为 ID 不存在，还是因为状态已经是目标状态
                        await cur.execute("SELECT id FROM recalc_signals WHERE request_id = %s", (req.request_id,))
                        if not await cur.fetchone():
                            raise HTTPException(status_code=404, detail="Signal request_id not found")
                        # 如果存在但未更新（可能 notes/status 一致），也视为成功
                    
                    await conn.commit()
                    
                    # 2. 如果失败，需要获取 ts_code 用于告警通知
                    if req.status == 'FAILED':
                        await cur.execute("SELECT ts_code FROM recalc_signals WHERE request_id = %s", (req.request_id,))
                        row = await cur.fetchone()
                        ts_code = row[0] if row else "Unknown"
                        
                        logger.warning(f"Recalc FAILED for {ts_code}: {req.notes}")
                        if notifier:
                            alert_msg = f"股票代码: {ts_code}\n请求ID: {req.request_id}\n错误信息: {req.notes}"
                            import asyncio
                            asyncio.create_task(notifier.send_alert(
                                title="E6 指标重算失败告警",
                                message=alert_msg,
                                level="warning"
                            ))
                    
                    return {"status": "success", "request_id": req.request_id}
                except HTTPException:
                    await conn.rollback()
                    raise
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"Ack operation failed: {e}")
                    raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ack failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
