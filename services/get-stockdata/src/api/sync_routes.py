from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Optional
from pydantic import BaseModel
import logging
import asyncio
import aiomysql
from core.sync_service import KLineSyncService

router = APIRouter(prefix="/api/v1/sync", tags=["synchronization"])
logger = logging.getLogger(__name__)

# ========== 风险缓解配置 ==========
SYNC_LOCK_KEY = "sync:lock:kline"      # 分布式锁的 Redis 键
SYNC_LOCK_TTL = 600                     # 锁超时时间 (10 分钟)
SYNC_TIMEOUT_SECONDS = 300              # 单阶段同步超时 (5 分钟)

class SyncRequest(BaseModel):
    mode: str = "smart"  # full, incremental, smart, created_at, by_stock_codes
    days: int = 7
    hours: int = 48
    batch_size: int = 10000
    sync_factors: bool = True
    stock_codes: Optional[list[str]] = None  # 用于 by_stock_codes 模式

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

async def _run_sync_task(request: SyncRequest, redis=None):
    """
    Background task wrapper for sync service.
    
    改进项:
    - P0: 超时熔断 - 使用 asyncio.wait_for 防止任务无限挂起
    - 统一异常处理和状态更新
    """
    service = KLineSyncService()
    try:
        await service.initialize()
        
        # 1. K-Line Sync (带超时保护)
        try:
            if request.mode == 'full':
                await asyncio.wait_for(
                    service.sync_full(batch_size=request.batch_size),
                    timeout=SYNC_TIMEOUT_SECONDS * 2  # 全量模式给双倍时间
                )
            elif request.mode == 'smart':
                await asyncio.wait_for(
                    service.sync_smart_incremental(),
                    timeout=SYNC_TIMEOUT_SECONDS
                )
            elif request.mode == 'created_at':
                await asyncio.wait_for(
                    service.sync_by_created_at(lookback_hours=request.hours, batch_size=request.batch_size),
                    timeout=SYNC_TIMEOUT_SECONDS
                )
            elif request.mode == 'by_stock_codes':
                if not request.stock_codes:
                    raise ValueError("by_stock_codes 模式需要提供 stock_codes 参数")
                await asyncio.wait_for(
                    service.sync_by_stock_codes(stock_codes=request.stock_codes),
                    timeout=SYNC_TIMEOUT_SECONDS
                )
            else:
                await asyncio.wait_for(
                    service.sync_smart_incremental(),
                    timeout=SYNC_TIMEOUT_SECONDS
                )
        except asyncio.TimeoutError:
            error_msg = f"K线同步超时 ({SYNC_TIMEOUT_SECONDS}s)"
            logger.error(error_msg)
            await service._update_status("failed", error_msg, 0.0)
            return
            
        # 2. Sequential Factor Sync (带超时保护)
        if request.sync_factors:
            try:
                logger.info("Starting sequential adjustment factor sync...")
                await asyncio.wait_for(
                    service.sync_adjust_factors(),
                    timeout=SYNC_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                error_msg = f"复权因子同步超时 ({SYNC_TIMEOUT_SECONDS}s)"
                logger.error(error_msg)
                await service._update_status("failed", error_msg, 0.0)
                return
            
    except Exception as e:
        logger.error(f"Background sync task failed: {e}", exc_info=True)
        try:
            await service._update_status("failed", f"同步失败: {str(e)}", 0.0)
        except Exception:
            pass  # 状态更新失败时不再抛出
    finally:
        await service.close()
        # 释放分布式锁
        if redis:
            try:
                await redis.delete(SYNC_LOCK_KEY)
                logger.info("✓ 分布式锁已释放")
            except Exception as e:
                logger.warning(f"释放分布式锁失败: {e}")

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
    
    改进项:
    - P0: 分布式锁 - 防止重复触发导致资源竞争
    """
    logger.info(f"Received sync request: {request}")
    
    # P0 改进: 分布式锁检查
    try:
        from data_access.redis_pool import RedisPoolManager
        redis = await RedisPoolManager.get_instance().get_redis()
        
        # 尝试获取分布式锁 (SETNX + TTL)
        lock_acquired = await redis.set(
            SYNC_LOCK_KEY, 
            "1", 
            ex=SYNC_LOCK_TTL, 
            nx=True
        )
        
        if not lock_acquired:
            # 锁已被占用，检查当前状态
            current_status = await redis.hget("sync:status:kline", "status")
            return {
                "status": "rejected",
                "message": f"任务已在运行中 (当前状态: {current_status or 'unknown'})",
                "check_status_url": "/api/v1/sync/kline/status"
            }
        
        logger.info("✓ 成功获取分布式锁")
        
        # 将锁传递给后台任务，由其负责释放
        background_tasks.add_task(_run_sync_task, request, redis)
        
    except Exception as e:
        logger.warning(f"分布式锁获取失败，降级为无锁模式: {e}")
        # 降级: 如果 Redis 不可用，仍然允许执行（但无锁保护）
        background_tasks.add_task(_run_sync_task, request, None)
    
    return {
        "status": "accepted", 
        "message": "Synchronization task started in background",
        "check_status_url": "/api/v1/sync/kline/status"
    }
