"""
盘后分笔数据同步任务入口

供 task-orchestrator 调用的临时任务
"""

import sys
import asyncio
import logging
import argparse
from datetime import datetime
from core.tick_sync_service import TickSyncService
from core.task_logger import TaskLogger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main(
    mode: str = 'incremental', 
    date: str = None, 
    scope: str = "config",
    shard_index: int = None,
    shard_total: int = None,
    distributed_source: str = "none",
    distributed_role: str = "consumer"
) -> int:
    """
    分笔数据同步主函数
    
    Args:
        mode: 'incremental' (增量/今日) | 'full' (全量，仅用于测试)
        date: 指定日期 YYYYMMDD，默认今日
        scope: 'config' (配置文件) | 'all' (全市场)
        shard_index: 分片索引 (0-based)，用于分布式采集
        shard_total: 总分片数，用于分布式采集
        
    Returns:
        int: 退出码 (0: 成功, 1: 失败)
    """
    shard_info = f", 分片={shard_index}/{shard_total}" if shard_index is not None else ""
    logger.info(f"启动分笔数据同步任务 (模式={mode}, 日期={date or '今日'}, 范围={scope}{shard_info})")
    
    service = TickSyncService()
    await service.initialize()
    
    start_time = datetime.now()
    
    try:
        # 获取股票池 (Consumer 模式不需要预先获取列表)
        # 获取股票池 (Consumer 模式不需要预先获取列表)
        if distributed_source == "redis" and distributed_role == "consumer":
            stock_codes = []
            logger.info("Consumer 模式: 跳过本地股票列表获取，将直接从 Redis 消费")
        elif scope == "all" and shard_index is not None:
            # 新架构: 直接从 Redis 获取已分片的股票列表
            logger.info(f"使用新架构分片: 从 Redis 获取 Shard {shard_index} 股票")
            stock_codes = await service.get_sharded_stocks(shard_index)
        else:
            stock_codes = await service.get_all_stocks() if scope == "all" else await service.get_stock_pool()
        
        # 应用分片过滤 (仅当使用旧逻辑且未通过 Redis 获取分片时)
        # 如果 stock_codes 是通过 get_sharded_stocks 获取的，则无需再次过滤
        if shard_index is not None and shard_total is not None and stock_codes and scope != "all":
            original_count = len(stock_codes)
            # 兼容旧的 hash 逻辑 (仅用于非全量或未连接 Redis 的情况)
            stock_codes = [
                code for code in stock_codes 
                if hash(code) % shard_total == shard_index
            ]
            logger.info(
                f"本地分片过滤: {original_count} 只 → {len(stock_codes)} 只 "
                f"(Shard {shard_index}/{shard_total})"
            )
        
        if distributed_role != "consumer":
            logger.info(f"待采集股票: {len(stock_codes)} 只")
        
        if distributed_source == "redis":
            if distributed_role == "producer":
                # Producer 模式: 推送任务
                logger.info("启动 Redis Producer 模式")
                count = await service.push_tasks_to_redis(stock_codes)
                logger.info(f"✅ 已推送 {count} 个任务到 Redis 队列")
                return 0
            else:
                # Consumer 模式: 消费任务
                logger.info("启动 Redis Consumer 模式")
                # 使用 consumer 循环逻辑
                # 原有的 sync_stocks 是并发处理列表，现在我们需要并发处理队列
                # 简单起见，我们在这里实现一个简单的 consumer loop wrapper 或者调用 service 方法
                # 由于 TickSyncService 中没有 loop 方法（之前打算加但后来决定放在这里更合适）
                
                # 定义消费者 worker
                semaphore = asyncio.Semaphore(6) # 总并发
                active_tasks = 0
                processed_count = 0
                failed_count = 0
                
                logger.info("开始监听 Redis 任务队列...")
                
                no_task_counter = 0
                max_idle_cycles = 10 # 20秒空闲退出
                
                # 定义消费者 worker
                # 让我们用一个更健壮的方式： Producer-Consumer 队列模式
                queue = asyncio.Queue(maxsize=10)
                
                async def worker():
                    nonlocal processed_count, failed_count
                    while True:
                        code = await queue.get()
                        try:
                            res = await service.sync_stock(code, date)
                            if res > 0: processed_count += 1
                            else: failed_count += 1
                            await service.ack_task_in_redis(code)
                        except Exception as e:
                            failed_count += 1
                            logger.error(f"处理任务 {code} 失败: {e}")
                        finally:
                            queue.task_done()
                
                # 启动 workers (先启动消费者，防止队列满导致死锁)
                workers = [asyncio.create_task(worker()) for _ in range(10)]

                # 1. 获取恢复任务列表（不立即入队，避免死锁）
                recovered_tasks = await service.recover_processing_tasks()
                recovered_iter = iter(recovered_tasks)
                recovery_mode = bool(recovered_tasks)
                
                logger.info(f"🔄 准备恢复 {len(recovered_tasks)} 个未完成任务")
                
                # Feeder loop (优先恢复任务，再消费 Redis)
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
                        if no_task_counter > (max_idle_cycles * 5) and queue.empty(): # 10s idle
                             break
                        await asyncio.sleep(0.5)
                
                # Wait for queue to empty
                await queue.join()
                for w in workers: w.cancel()
                
                results = {"success": processed_count, "failed": failed_count, "total_records": processed_count} # Approx
                
        else:
            # 原始模式: 直接并发列表
            results = await service.sync_stocks(
                stock_codes=stock_codes,
                trade_date=date,
                concurrency=6
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
                f"⚠️ 分笔同步部分失败: "
                f"成功 {results['success']}, 失败 {results['failed']}"
            )
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
        default="incremental",
        choices=["incremental", "full"],
        help="同步模式: incremental(增量/今日) 或 full(全量)"
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
        default=None,
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
    args = parser.parse_args()
    
    exit_code = asyncio.run(main(
        args.mode, 
        args.date, 
        args.scope,
        args.shard_index,
        args.shard_total,
        args.distributed_source,
        args.distributed_role
    ))
    sys.exit(exit_code)
