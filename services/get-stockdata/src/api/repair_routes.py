"""
数据修复 API 路由
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional
import logging
import aiohttp
import asynch
import asyncio
import os
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

router = APIRouter(prefix="/api/v1/repair", tags=["data-repair"])
logger = logging.getLogger(__name__)

# 模型
class BatchRepairRequest(BaseModel):
    stock_codes: list[str]

# 配置
COLLECT_SERVICE_URL = os.getenv("BAOSTOCK_API_URL", "http://124.221.80.250:8001")
SYNC_API_URL = os.getenv("SYNC_API_URL", "http://127.0.0.1:8083")  # host network mode
PROXY_URL = os.getenv("PROXY_URL")  # 代理配置

# 全局 ClickHouse 连接池（单例）
_clickhouse_pool = None


async def get_clickhouse_pool():
    """
    依赖注入: 获取 ClickHouse 连接池（全局单例）
    """
    global _clickhouse_pool
    
    if _clickhouse_pool is None:
        ch_host = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
        ch_port = int(os.getenv('CLICKHOUSE_PORT', 9000))
        ch_user = os.getenv('CLICKHOUSE_USER', 'default')
        ch_password = os.getenv('CLICKHOUSE_PASSWORD', '')
        ch_database = os.getenv('CLICKHOUSE_DATABASE', 'stock_data')
        
        _clickhouse_pool = await asynch.create_pool(
            host=ch_host,
            port=ch_port,
            user=ch_user,
            password=ch_password,
            database=ch_database,
            minsize=1,
            maxsize=3
        )
        logger.info("✓ ClickHouse 连接池已创建（用于数据修复）")
    
    return _clickhouse_pool


async def _clear_clickhouse_stock(stock_code: str, ch_pool):
    """清除 ClickHouse 中指定股票的数据"""
    async with ch_pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = "ALTER TABLE stock_kline_daily DELETE WHERE stock_code = %(code)s"
            await cursor.execute(sql, {"code": stock_code})
            logger.info(f"✓ 已清除 ClickHouse 中 {stock_code} 的数据")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
)
async def _trigger_remote_collect(stock_code: str, start_date: str = "1990-01-01"):
    """调用远程采集服务（带重试）"""
    url = f"{COLLECT_SERVICE_URL}/api/v1/collect/stock_history"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            json={
                "stock_code": stock_code,
                "start_date": start_date,
                "clear_existing": True
            },
            proxy=PROXY_URL,  # 使用代理
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status not in [200, 202]:  # 接受 200 OK 和 202 Accepted
                text = await response.text()
                raise HTTPException(
                    status_code=500,
                    detail=f"远程采集服务调用失败: {response.status} - {text}"
                )
            
            result = await response.json()
            logger.info(f"✓ 远程采集任务已启动: task_id={result.get('task_id')}")
            return result


async def _check_task_status(task_id: str, max_wait: int = 300):
    """
    轮询检查采集任务状态
    
    Args:
        task_id: 任务ID
        max_wait: 最大等待时间（秒），默认5分钟
    """
    url = f"{COLLECT_SERVICE_URL}/api/v1/collect/task/{task_id}"
    
    # 每5秒轮询一次
    for i in range(max_wait // 5):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    proxy=PROXY_URL,  # 使用代理
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        status = result.get("status")
                        progress = result.get("progress", 0)
                        
                        if status == "success":
                            logger.info(f"✓ 采集任务完成: {result.get('records_collected')} 条记录")
                            return result
                        elif status == "failed":
                            raise HTTPException(
                                status_code=500,
                                detail=f"采集任务失败: {result.get('error')}"
                            )
                        elif status in ["pending", "running"]:
                            logger.info(f"采集任务进行中: {progress}%")
                            await asyncio.sleep(5)
                            continue
        except aiohttp.ClientError as e:
            logger.warning(f"查询任务状态失败: {e}，将重试")
            await asyncio.sleep(5)
            continue
    
    raise HTTPException(status_code=504, detail=f"采集任务超时（超过{max_wait}秒）")


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=5)
)
async def _trigger_sync(stock_codes: list[str]):
    """
    触发同步任务（从 MySQL 到 ClickHouse）
    
    使用 by_stock_codes 模式同步指定股票的全部历史数据
    """
    url = f"{SYNC_API_URL}/api/v1/sync/kline"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            json={
                "mode": "by_stock_codes",
                "stock_codes": stock_codes
            },
            timeout=aiohttp.ClientTimeout(total=300)
        ) as response:
            if response.status == 200:
                result = await response.json()
                logger.info(f"✓ 批量同步任务已触发: {result}")
            else:
                logger.warning(f"同步触发失败: {response.status}")


async def _rebuild_single_stock_internal(stock_code: str, ch_pool):
    """
    单个股票重建的内部核心逻辑
    """
    # 固定从1990-01-01开始，确保全量重建
    start_date = "1990-01-01"
    
    # Step 1: 清除 ClickHouse
    await _clear_clickhouse_stock(stock_code, ch_pool)
    
    # Step 2: 调用远程采集
    collect_result = await _trigger_remote_collect(stock_code, start_date)
    task_id = collect_result.get("task_id")
    
    if not task_id:
        raise Exception(f"股票 {stock_code} 未获取到采集任务ID")
    
    # Step 3: 等待采集完成（最多5分钟）
    task_result = await _check_task_status(task_id, max_wait=300)
    return task_result


async def _run_batch_rebuild_task(stock_codes: list[str], ch_pool):
    """
    后台执行批量重建任务
    """
    success_codes = []
    failed_codes = []
    
    for code in stock_codes:
        try:
            logger.info(f"正在进行批量重建: {code} ...")
            await _rebuild_single_stock_internal(code, ch_pool)
            success_codes.append(code)
        except Exception as e:
            logger.error(f"批量重建中股票 {code} 失败: {e}")
            failed_codes.append(code)
            
    # 如果有成功的，触发一次性批量同步
    if success_codes:
        logger.info(f"批量重建采集阶段完成，开始同步 {len(success_codes)} 只股票")
        await _trigger_sync(success_codes)
        
    logger.info(f"✨ 批量重建任务结束: 成功={len(success_codes)}, 失败={len(failed_codes)}")


@router.post("/stock/{stock_code}")
async def rebuild_stock(
    stock_code: str,
    ch_pool = Depends(get_clickhouse_pool)
):
    """
    个股全量重建 (同步等待模式)
    """
    logger.info(f"🔧 开始全量重建股票 {stock_code} 的数据")
    
    try:
        task_result = await _rebuild_single_stock_internal(stock_code, ch_pool)
        
        # 触发单只同步
        await _trigger_sync([stock_code])
        
        return {
            "status": "success",
            "stock_code": stock_code,
            "records_collected": task_result.get("records_collected"),
            "message": f"✓ 股票 {stock_code} 数据重建完成"
        }
        
    except Exception as e:
        logger.error(f"❌ 股票重建失败: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def rebuild_batch(
    request: BatchRepairRequest,
    background_tasks: BackgroundTasks,
    ch_pool = Depends(get_clickhouse_pool)
):
    """
    批量个股重建 (异步后台模式)
    """
    if not request.stock_codes:
        raise HTTPException(status_code=400, detail="未提供股票代码列表")
        
    logger.info(f"📦 收到批量重建请求: {len(request.stock_codes)} 只股票")
    
    # 启动后台任务
    background_tasks.add_task(_run_batch_rebuild_task, request.stock_codes, ch_pool)
    
    return {
        "status": "accepted",
        "message": f"已启动 {len(request.stock_codes)} 只股票的异步重建任务",
        "check_logs": "请通过服务日志查看进度"
    }


@router.get("/stock/{stock_code}/status")
async def get_rebuild_status(stock_code: str):
    """
    查询重建状态（预留接口）
    """
    return {
        "stock_code": stock_code,
        "status": "not_implemented",
        "message": "当前版本使用同步重建，无需状态查询"
    }
