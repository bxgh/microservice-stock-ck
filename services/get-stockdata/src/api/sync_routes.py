from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Optional
from pydantic import BaseModel
import logging
import aiomysql
from core.sync_service import KLineSyncService

router = APIRouter(prefix="/api/v1/sync", tags=["synchronization"])
logger = logging.getLogger(__name__)

class SyncRequest(BaseModel):
    mode: str = "smart"  # full, incremental, smart, created_at
    days: int = 7
    hours: int = 48
    batch_size: int = 10000
    sync_factors: bool = True

@router.get("/kline/status")
async def get_sync_status():
    """
    Get current synchronization status from Redis.
    """
    try:
        from data_access.redis_pool import RedisPoolManager
        redis = await RedisPoolManager.get_instance().get_redis()
        status = await redis.hgetall("sync:status:kline")
        if not status:
            return {"status": "unknown", "message": "No sync status available"}
        return status
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve status")

async def _run_sync_task(request: SyncRequest):
    """Background task wrapper for sync service"""
    service = KLineSyncService()
    try:
        await service.initialize()
        
        # 1. K-Line Sync
        if request.mode == 'full':
            await service.sync_full(batch_size=request.batch_size)
        elif request.mode == 'smart':
            await service.sync_smart_incremental()
        elif request.mode == 'created_at':
            await service.sync_by_created_at(lookback_hours=request.hours, batch_size=request.batch_size)
        else:
            await service.sync_incremental(days=request.days)
            
        # 2. Sequential Factor Sync
        if request.sync_factors:
            logger.info("Starting sequential adjustment factor sync...")
            await service.sync_adjust_factors()
            
    except Exception as e:
        logger.error(f"Background sync task failed: {e}", exc_info=True)
        # Service handles status update to 'failed' internally in most cases, 
        # but we can ensure it if needed.
    finally:
        await service.close()

@router.get("/kline/history")
async def get_sync_history(limit: int = 7):
    """
    Get sync execution history from MySQL logs.
    """
    service = KLineSyncService()
    try:
        await service.initialize()
        async with service.mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT task_name, execution_time, status, records_processed, details, duration_seconds 
                    FROM sync_execution_logs 
                    ORDER BY execution_time DESC 
                    LIMIT %s
                """
                await cursor.execute(sql, (limit,))
                rows = await cursor.fetchall()
                # Format datetime objects
                for row in rows:
                    if row['execution_time']:
                        row['execution_time'] = row['execution_time'].strftime('%Y-%m-%d %H:%M:%S')
                return rows
    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch history")
    finally:
        await service.close()

@router.post("/kline")
async def sync_kline_data(request: SyncRequest, background_tasks: BackgroundTasks):
    """
    Trigger K-Line data synchronization (Async Background Task).
    """
    logger.info(f"Received sync request: {request}")
    
    # Check if a sync is already running? 
    # For now, we trust the user or Redis lock could be added later.
    
    background_tasks.add_task(_run_sync_task, request)
    
    return {
        "status": "accepted", 
        "message": "Synchronization task started in background",
        "check_status_url": "/api/v1/sync/kline/status"
    }
