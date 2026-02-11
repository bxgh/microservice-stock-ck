"""
盘后分笔数据同步任务入口

供 task-orchestrator 调用的临时任务
"""

import sys
import asyncio
import logging
import argparse
from datetime import datetime, timedelta
import xxhash
import pytz
from core.tick_sync_service import TickSyncService
from core.task_logger import TaskLogger

# 上海时区
CST = pytz.timezone('Asia/Shanghai')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 常量定义
CONSUMER_MAX_IDLE_CYCLES = 10  # 队列最大轮询空闲次数 (5秒)


async def main(
    mode: str = None, 
    date: str = None, 
    scope: str = None,
    shard_index: int = None,
    shard_total: int = None,
    distributed_source: str = "none",
    distributed_role: str = "consumer",
    concurrency: int = 60,
    stock_codes: list = None,
    idempotent: bool = False,
    force_all: bool = False
) -> int:
    """
    分笔数据同步主函数
    """
    # [New V4.0] 优先读取环境变量 (Orchestrator 注入)
    mode = mode or os.getenv("SYNC_MODE") or "repair"
    scope = scope or os.getenv("SYNC_SCOPE") or "config"
    date = date or os.getenv("SYNC_DATE")
    
    shard_info = f", 分片={shard_index}/{shard_total}" if shard_index is not None else ""
    
    # 获取目标日期：6:00 AM 之前使用前一日
    now = datetime.now(CST)
    if date:
        # 如果明确指定了日期，使用指定日期
        target_date = date
    else:
        # 未指定日期时，应用 6AM 规则
        if now.hour < 6:
            yesterday = now - timedelta(days=1)
            target_date = yesterday.strftime("%Y%m%d")
            logger.info(f"⏰ 当前时间 {now.strftime('%H:%M')} < 06:00，使用前一交易日 {target_date}")
        else:
            target_date = now.strftime("%Y%m%d")
    
    logger.info(f"启动分笔数据同步任务 (模式={mode}, 日期={target_date}, 范围={scope}{shard_info}, 并发={concurrency})")
    
    service = TickSyncService()
    await service.initialize()
    
    start_time = datetime.now()
    idempotent_next = idempotent  # 默认使用命令行传入的参数
    
    # 1. 获取待处理股票列表 (统一由 TickSyncService 编排，支持分片与自动过滤)
    try:
        if mode == "full":
            logger.info(f"🚀 全量重建模式: 正在清理 {target_date} 全天数据...")
            # 获取全市场名单 (带分片)
            stock_codes = await service.fetch_sync_list(
                scope="all", 
                trade_date=target_date,
                shard_index=shard_index,
                shard_total=shard_total
            )
            # 只有在非分片模式或分片0时，才执行全表物理清理 (避免重复操作导致 ClickHouse Mutation 堆积)
            if shard_index is None or shard_index == 0:
                # 全量模式根据参数决定是否强制清场
                await service.purge_tick_data(target_date, stock_codes=None, force_all=force_all)
            idempotent_next = False # 已经提前清场
            
        elif mode == "repair":
            if not stock_codes:
                logger.error("❌ Repair 模式必须通过 --stock-codes 指定代码")
                return 1
            
            if len(stock_codes) > 200:
                logger.warning(f"⚠️ 修复数量({len(stock_codes)}) > 200，自动升级为全天全量重建")
                stock_codes = await service.fetch_sync_list(
                    scope="all", 
                    trade_date=target_date,
                    shard_index=shard_index,
                    shard_total=shard_total
                )
                if shard_index is None or shard_index == 0:
                    # 修复模式自动升级全量时，受 Safety Valve 保护 (除非显式传 force_all)
                    await service.purge_tick_data(target_date, stock_codes=None, force_all=force_all)
                idempotent_next = False
            else:
                # [New V4.0] 定向修复模式也需要过滤停牌，防止无效补采
                try:
                    suspended = await service.stock_universe.get_suspended_stocks(target_date)
                    if suspended:
                        suspended_set = set(suspended)
                        before_count = len(stock_codes)
                        stock_codes = [s for s in stock_codes if s not in suspended_set]
                        if before_count > len(stock_codes):
                            logger.info(f"🛡️ 定向修复中剔除 {before_count - len(stock_codes)} 只停牌股票 ({target_date})")
                except Exception as e:
                    logger.warning(f"⚠️ 定向修复过滤停牌失败: {e}")

                if not stock_codes:
                    logger.info("✅ 修复名单为空 (审计全覆盖)，无需补采。")
                    return 0

                logger.info(f"🛠️ 定向修复模式: 正在清理并重抓 {len(stock_codes)} 只个股...")
                # 仅清理指定股票
                await service.purge_tick_data(target_date, stock_codes=stock_codes)
                idempotent_next = False
        
        # 兜底：如果 stock_codes 仍为空且非生产者模式，则根据 scope 获取默认名单
        if not stock_codes and not (distributed_source == "redis" and distributed_role == "consumer"):
             stock_codes = await service.fetch_sync_list(
                scope=scope, 
                trade_date=target_date,
                shard_index=shard_index,
                shard_total=shard_total
            )

        logger.info(f"待同步股票总数: {len(stock_codes)} 只")
        
        if distributed_source == "redis":
            # ... (distributed logic remains same)
            pass
        
        if distributed_source == "redis":
            if distributed_role == "producer":
                # Producer 模式: 推送任务
                logger.info("启动 Redis Producer 模式")
                count = await service.push_tasks_to_redis(stock_codes)
                logger.info(f"✅ 已推送 {count} 个任务到 Redis 队列")
                return 0
            else:
                # Consumer 模式: 消费任务
                logger.info(f"启动 Redis Consumer 模式 (并发: {concurrency})")
                
                # 定义消费者 worker
                semaphore = asyncio.Semaphore(concurrency) # 总并发
                stats_lock = asyncio.Lock()
                active_tasks = 0
                processed_count = 0
                failed_count = 0
                
                logger.info("开始监听 Redis 任务队列...")
                
                # 定义消费者 worker - Producer-Consumer 队列模式
                queue = asyncio.Queue(maxsize=concurrency * 2)
                
                async def worker():
                    nonlocal processed_count, failed_count
                    while True:
                        code = await queue.get()
                        async with semaphore:
                            try:
                                # Consumer 模式不执行 force/idempotent，假设 Producer 已处理
                                res = await service.sync_stock(code, target_date)
                                async with stats_lock:
                                    if res > 0: processed_count += 1
                                    else: failed_count += 1
                                await service.ack_task_in_redis(code)
                            except Exception as e:
                                async with stats_lock:
                                    failed_count += 1
                                logger.error(f"处理任务 {code} 失败: {e}")
                            finally:
                                queue.task_done()
                
                # 启动 workers
                workers = [asyncio.create_task(worker()) for _ in range(concurrency)]

                # 1. 获取恢复任务列表
                recovered_tasks = await service.recover_processing_tasks()
                recovered_iter = iter(recovered_tasks)
                recovery_mode = bool(recovered_tasks)
                
                logger.info(f"🔄 准备恢复 {len(recovered_tasks)} 个未完成任务")
                
                no_task_counter = 0
                
                # Feeder loop
                while True:
                    # 优先处理恢复任务
                    if recovery_mode:
                        try:
                            task_code = next(recovered_iter)
                            await queue.put(task_code)
                            continue
                        except StopIteration:
                            recovery_mode = False
                            logger.info("✅ 恢复任务已全部入队，切换到正常消费模式")
                    
                    # 正常消费 Redis
                    task_code = await service.consume_task_from_redis()
                    if task_code:
                        await queue.put(task_code)
                        no_task_counter = 0
                    else:
                        no_task_counter += 1
                        if no_task_counter > CONSUMER_MAX_IDLE_CYCLES and queue.empty(): # 5s idle
                             break
                        await asyncio.sleep(0.5)
                
                # Wait for queue to empty
                await queue.join()
                for w in workers: w.cancel()
                
                results = {"success": processed_count, "failed": failed_count, "total_records": processed_count}
                
        else:
            # 模式: 直接并发列表
            results = await service.sync_stocks(
                stock_codes=stock_codes,
                trade_date=target_date,
                concurrency=concurrency,
                force=True,
                idempotent=idempotent_next
            )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # 判断结果
        if results["failed"] == 0:
            logger.info(
                f"✅ 分笔同步完成: "
                f"{results['success']} 只股票, "
                f"{results['total_records']:,} 条记录, "
                f"耗时 {duration:.1f}s"
            )
            return 0
        else:
            logger.warning(
                f"成功 {results['success']}, 失败 {results['failed']}"
            )
            if results.get("failed_codes"):
                logger.warning(f"失败/无数据代码: {results['failed_codes']}")
            if results.get("errors"):
                logger.warning(f"异常详情 (Top 50): {results['errors'][:50]}")
            return 1 if results["failed"] > results["success"] else 0
            
    except Exception as e:
        logger.error(f"❌ 分笔同步任务异常: {e}", exc_info=True)
        return 1
    finally:
        await service.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="分笔数据同步任务")
    parser.add_argument(
        "--mode", 
        type=str, 
        default=None,
        choices=["full", "repair"],
        help="同步模式: full(全量重建) 或 repair(定向修复)"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="指定日期 YYYYMMDD，默认今日"
    )
    parser.add_argument("--scope", type=str, default="config", choices=["config", "all"], help="同步范围: config(配置文件) 或 all(全市场)")
    parser.add_argument(
        "--shard-index",
        type=int,
        default=None,
        help="分片索引 (0-based)，用于分布式采集"
    )
    parser.add_argument(
        "--shard-total",
        type=int,
        default=3,
        help="总分片数，用于分布式采集"
    )
    parser.add_argument(
        "--distributed-source",
        type=str,
        default="none",
        choices=["none", "redis"],
        help="分布式任务来源: none(不使用) 或 redis(Redis队列)"
    )
    parser.add_argument(
        "--distributed-role",
        type=str,
        default="consumer",
        choices=["producer", "consumer"],
        help="分布式角色: producer(生产者) 或 consumer(消费者)"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=60,
        help="并发任务数 (默认为 60)"
    )
    parser.add_argument(
        "--stock-code", "--stock-codes",
        type=str,
        default=None,
        dest="stock_codes",
        help="手动指定股票代码，逗号分隔"
    )
    parser.add_argument(
        "--shard-id",
        type=int,
        default=None,
        help="分片ID (Alias for shard-index)"
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="[危险] 允许强制全量删除全天数据 (跳过安全阈值)"
    )
    parser.add_argument(
        "--idempotent",
        action="store_true",
        help="同步前强制清理对应股票的旧数据 (幂等模式)"
    )
    args, unknown = parser.parse_known_args()
    if unknown:
        logger.info(f"Ignored unknown arguments: {unknown}")
    
    # 兼容处理 shard_id -> shard_index
    if args.shard_index is None and args.shard_id is not None:
        args.shard_index = args.shard_id
    
    # 解析股票代码
    passed_codes = None
    if args.stock_codes:
        passed_codes = [c.strip() for c in args.stock_codes.split(',') if c.strip()]

    exit_code = asyncio.run(main(
        args.mode, 
        args.date, 
        args.scope,
        args.shard_index,
        args.shard_total,
        args.distributed_source,
        args.distributed_role,
        args.concurrency,
        passed_codes,
        idempotent=args.idempotent,
        force_all=args.force_all
    ))
    sys.exit(exit_code)
