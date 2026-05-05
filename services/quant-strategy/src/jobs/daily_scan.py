#!/usr/bin/env python3
"""
每日量化选股任务入口 (Daily Strategy Scan Job)
用于调度中心 (task-orchestrator) 调用，执行长线候选池刷新。
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# 确保 src 目录在路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from adapters.stock_data_provider import data_provider
from database import init_database, close_database
from services.alpha.fundamental_scoring_service import fundamental_scoring_service
from services.alpha.valuation_service import valuation_service
from services.fundamental_filter import FundamentalFilter
from services.stock_pool.candidate_service import CandidatePoolService
from orchestrator.selection_report_generator import selection_report_generator

logger = logging.getLogger(__name__)

async def run_daily_scan():
    """执行每日选股扫描"""
    logger.info("🚀 开始执行每日量化选股任务...")
    
    try:
        # 1. 数据库初始化
        logger.info("正在初始化数据库连接...")
        await init_database()
        
        # 2. 数据提供者与服务量产初始化
        logger.info("正在初始化数据适配器与 Alpha 评分服务...")
        await data_provider.initialize()
        
        fundamental_filter = FundamentalFilter()
        
        # 3. 实例化候选池服务并注入真实服务
        candidate_service = CandidatePoolService(
            data_provider=data_provider,
            fundamental_scoring=fundamental_scoring_service,
            valuation_service=valuation_service,
            fundamental_filter=fundamental_filter
        )
        
        # 4. 执行选股刷新 (长线池)
        # 环境变量控制 limit，默认为 None (全量扫描)
        pool_limit = os.getenv("POOL_LIMIT")
        limit = int(pool_limit) if pool_limit else None
        
        logger.info(f"正在刷新长线候选池 (Limit: {limit if limit else 'Full Scan'})...")
        count = await candidate_service.refresh_pool(pool_type='long', limit=limit)
        
        logger.info(f"✅ 选股完成！共选出 {count} 只长线候选标的。")
        
        # 5. 获取结果并生成日报
        results = await candidate_service.get_candidates(pool_type='long', limit=10)
        
        # 自动生成 Markdown 报告
        target_date = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"正在生成选股日报 ({target_date})...")
        report_path = selection_report_generator.generate_daily_report(
            date=target_date, 
            candidates=results, 
            pool_type='long'
        )
        if report_path:
            logger.info(f"✨ 选股日报生成成功: {report_path}")

        # 6. 打印 Top 10 结果以便日志审计
        logger.info("🏆 Top 10 筛选结果：")
        for idx, stock in enumerate(results, 1):
            logger.info(f"{idx}. {stock.code} | 分数: {stock.score:.2f} | 细分池: {stock.sub_pool}")
            
    except Exception as e:
        logger.error(f"❌ 选股任务执行失败: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        # 资源清理
        logger.info("清理资源并关闭连接...")
        await data_provider.close()
        await close_database()

def main():
    """入口函数"""
    # 设置日志格式
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(run_daily_scan())

if __name__ == "__main__":
    main()
