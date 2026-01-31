#!/usr/bin/env python3
"""
盘中分笔数据校验与补采 Job

功能：
1. 检查 tick_data_intraday 表的覆盖率
2. 如果覆盖率低于阈值，自动补采缺失股票
3. 将结果写入 MySQL 审计表

使用：
  python -m jobs.intraday_tick_validation --session noon
  python -m jobs.intraday_tick_validation --session close --dry-run
"""

import asyncio
import logging
import sys
import argparse
from datetime import datetime
import pytz

from core.tick_sync_service import TickSyncService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("IntradayTickValidation")
CST = pytz.timezone('Asia/Shanghai')



async def save_audit_summary(data_type: str, session: str, trade_date: str, coverage: float, missing_count: int, service: TickSyncService):
    """将审计结果写入 MySQL data_audit_summaries 表"""
    try:
        # 构造审计记录
        level = 'PASS' if coverage >= 0.95 else 'WARNING'
        description = f"Session {session}: Coverage {coverage:.1%} ({missing_count} missing)"
        
        async with service.clickhouse_pool.acquire() as conn:
            # 注意：这里应该写入 MySQL，但为了简化，先写入日志
            # TODO: 实现 MySQL 审计表写入逻辑
            logger.info(f"📝 审计记录: data_type={data_type}, target=session_{session}, level={level}, desc={description}")
            
    except Exception as e:
        logger.error(f"❌ 写入审计表失败: {e}")


async def main():
    parser = argparse.ArgumentParser(description="盘中分笔数据校验与补采")
    parser.add_argument("--session", choices=["noon", "close"], required=True, help="校验时段 (noon: 午休, close: 盘后)")
    parser.add_argument("--dry-run", action="store_true", help="仅检查不补采")
    parser.add_argument("--threshold", type=float, default=0.98, help="覆盖率阈值 (默认 0.98)")
    parser.add_argument("--date", type=str, help="指定日期 (YYYYMMDD)，不指定则使用今天")
    
    args = parser.parse_args()
    
    logger.info(f"🚀 启动盘中分笔校验 (session={args.session}, dry_run={args.dry_run})")
    
    service = TickSyncService()
    await service.initialize()
    
    try:
        # 1. 确定交易日期
        if args.date:
            try:
                dt = datetime.strptime(args.date, "%Y%m%d")
                trade_date = dt.strftime("%Y-%m-%d")
            except ValueError:
                trade_date = args.date
        else:
            trade_date = datetime.now(CST).strftime("%Y-%m-%d")
        
        logger.info(f"📅 目标日期: {trade_date}")
        
        # 2. 获取全量股票名单 (Inventory)
        # 统一使用 fetch_sync_list 保证名单标准化
        try:
            expected_codes = await service.fetch_sync_list(scope="all")
            if not expected_codes:
                logger.error("❌ 未能获取全量股票名单，退出")
                return
            logger.info(f"✅ 股票池加载完成: 共 {len(expected_codes)} 只")
        except Exception as e:
            logger.error(f"❌ 加载股票池失败: {e}")
            return
        
        # 3. 调用扩展的 check_intraday_coverage()
        expected, actual, missing = await service.validator.check_intraday_coverage(
            expected_codes, trade_date, session=args.session
        )
        
        coverage = actual / expected if expected > 0 else 0
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 校验结果:")
        logger.info(f"  预期股票数: {expected}")
        logger.info(f"  实际采集数: {actual}")
        logger.info(f"  覆盖率: {coverage:.2%}")
        logger.info(f"  缺失股票数: {len(missing)}")
        logger.info(f"{'='*60}\n")
        
        # 4. 写入 MySQL 审计表
        await save_audit_summary('intraday_tick', args.session, trade_date, coverage, len(missing), service)
        
        # 5. 如果有缺失且非 dry-run，执行补采
        if missing and not args.dry_run:
            if coverage < args.threshold:
                logger.info(f"🔧 覆盖率 ({coverage:.1%}) 低于阈值 ({args.threshold:.0%})，准备修复 {len(missing)} 只股票...")
                
                # [NEW] 修复前清算：删除已有残缺数据，防止重复
                # 对于午盘校验，即使是存在的也会被重拉(如果没过校验)
                await service.purge_tick_data(trade_date, missing)
                
                # 直接复用现有 sync_stocks()
                # 修复版本: 设置 idempotent=False，因为前面已经批量清理过了
                results = await service.sync_stocks(missing, trade_date, concurrency=64, idempotent=False)
                
                logger.info(f"\n✅ 补采完成:")
                logger.info(f"  成功: {results['success']}")
                logger.info(f"  失败: {results['failed']}")
                logger.info(f"  跳过: {results['skipped']}")
                logger.info(f"  总写入: {results['total_records']} 条")
            else:
                logger.info(f"✓ 覆盖率达标，无需补采")
        elif missing and args.dry_run:
            logger.info(f"[DRY-RUN] 发现 {len(missing)} 只缺失股票，示例:")
            for code in missing[:5]:
                logger.info(f"  - {code}")
        else:
            logger.info("✅ 无缺失股票")
        
    except Exception as e:
        logger.error(f"❌ 校验任务失败: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await service.close()


if __name__ == "__main__":
    asyncio.run(main())
