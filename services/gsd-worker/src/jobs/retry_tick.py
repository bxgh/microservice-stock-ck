
import asyncio
import logging
import argparse
import sys
from datetime import datetime
import pytz
from core.tick_sync_service import TickSyncService

# 上海时区
CST = pytz.timezone('Asia/Shanghai')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_retry(date: str = None, dry_run: bool = False, concurrency: int = 5):
    """
    自动补采脚本主逻辑
    """
    today_str = datetime.now(CST).strftime("%Y%m%d")
    target_date = date if date else today_str
    
    logger.info(f"🔍 启动自动质量检查与补采: 日期={target_date}, DryRun={dry_run}")
    
    service = TickSyncService()
    await service.initialize()
    
    try:
        if not service.redis_client:
            logger.error("❌ Redis 未连接，无法读取状态")
            return
        
        status_key = f"tick_sync:status:{target_date}"
        # 获取所有已记录的股票状态
        all_status = await service.redis_client.hgetall(status_key)
        
        if not all_status:
            logger.warning(f"⚠️ Redis 中未发现日期 {target_date} 的采集记录")
            return
        
        retry_list = []
        
        for code, value in all_status.items():
            # 格式: status|count|start_t|end_t|sync_time|error
            parts = value.split('|')
            if len(parts) < 6:
                continue
            
            status = parts[0]
            start_t = parts[2]
            
            needs_retry = False
            reason = ""
            
            # 1. 明确标记为失败
            if status == "failed":
                needs_retry = True
                reason = "状态标记为失败"
            
            # 2. 数据不全 (缺少 09:25 集合竞价)
            # 注意：某些极不活跃股票可能确实没有 09:25，但 09:30 以后才有
            # 这里保守一点，如果 > 09:25 且 < 09:35，认为可能漏了
            elif start_t and start_t > "09:25":
                needs_retry = True
                reason = f"数据开始时间晚于 09:25 ({start_t})"
                
            if needs_retry:
                retry_list.append((code, reason))
        
        logger.info(f"📊 扫描完成: 发现 {len(retry_list)} 只股票需要补采")
        
        if dry_run:
            for code, reason in retry_list:
                logger.info(f"  [DryRun] {code}: {reason}")
            return
        
        if not retry_list:
            logger.info("✅ 未发现异常数据，无需补采")
            return
        
        # 执行补采
        logger.info(f"🚀 开始补采 {len(retry_list)} 只股票 (并发={concurrency})...")
        
        # 重用 service.sync_stocks 的逻辑
        codes_to_retry = [item[0] for item in retry_list]
        results = await service.sync_stocks(
            stock_codes=codes_to_retry,
            trade_date=target_date,
            concurrency=concurrency
        )
        
        logger.info(f"✅ 补采完成: 成功 {results['success']}, 失败 {results['failed']}")
        
    finally:
        await service.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="分笔数据自动补采脚本")
    parser.add_argument("--date", type=str, help="指定日期 YYYYMMDD")
    parser.add_argument("--dry-run", action="store_true", help="仅查看不执行")
    parser.add_argument("--concurrency", type=int, default=5, help="补采并发数")
    
    args = parser.parse_args()
    asyncio.run(run_retry(args.date, args.dry_run, args.concurrency))
