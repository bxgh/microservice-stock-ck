import asyncio
import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends
from starlette.requests import Request

from src.core.config import settings
from src.core.dependencies import ConfigLoader
from src.core.github_client import GitHubClient
from src.collectors.github import GitHubCollector
from src.collectors.hardware_spot import HardwareSpotCollector
from src.collectors.procurement import ProcurementCollector
from src.storage.clickhouse import ClickHouseDAO
from src.models.metrics import RepoMetrics

logger = logging.getLogger(__name__)

router = APIRouter()


async def sync_all_altdata_job(ch_dao: ClickHouseDAO):
    """
    全链路同步作业核心：
    1. 同步 GitHub 开源社区指标 (Module A)
    2. 同步云端 GPU 现货价格指标 (Module B - Story 18.1)
    3. 同步政企招投标算力投入 (Module B - Story 18.2)
    """
    logger.info("=== Start full alternative data sync ===")
    
    # --- Part 1: GitHub Metrics ---
    try:
        repos_config = ConfigLoader.load_repositories()
        tokens = settings.github_token_list
        if tokens:
            client = GitHubClient(tokens=tokens)
            collector = GitHubCollector(client)
            metrics_list: List[RepoMetrics] = []
            
            for conf in repos_config:
                for repo in conf.repos:
                    await asyncio.sleep(1.0)
                    metric = await collector.collect_repo(org=conf.org, repo=repo, label=conf.label)
                    if metric:
                        metrics_list.append(metric)
            
            if metrics_list:
                ch_dao.insert_metrics(metrics_list)
            await client.close()
    except Exception as e:
        logger.error(f"GitHub metrics sync failed: {e}")

    # --- Part 2: Hardware Spot Prices (Story 18.1) ---
    try:
        hw_config = ConfigLoader.load_hardware_config()
        collector = HardwareSpotCollector()
        prices = await collector.collect_all(hw_config)
        
        if prices:
            ch_dao.insert_hardware_prices(prices)
            logger.info(f"Hardware price sync completed: {len(prices)} records.")
    except Exception as e:
        logger.error(f"Hardware price sync failed: {e}")

    # --- Part 3: Procurement Tenders (Story 18.2) ---
    try:
        # 定义核心监控关键词，包含用户提到的沐曦股份及其产品
        keywords = ["华为昇腾", "沐曦", "海光DCU", "服务器", "智算中心", "算力"]
        collector = ProcurementCollector()
        tenders = await collector.collect_tenders(keywords)
        
        if tenders:
            ch_dao.insert_procurement_tenders(tenders)
            logger.info(f"Procurement tender sync completed: {len(tenders)} records.")
    except Exception as e:
        logger.error(f"Procurement tender sync failed: {e}")
        
    logger.info("=== Full sync job finished ===")


@router.post("/trigger_sync", summary="手动触发全链路数据同步 (Github + Hardware)")
async def trigger_sync(request: Request, background_tasks: BackgroundTasks):
    """
    触发 Github 指标与硬件现货价格的同步。
    """
    ch_dao: ClickHouseDAO = request.app.state.ch_dao
    background_tasks.add_task(sync_all_altdata_job, ch_dao)
    
    return {
        "status": "Accepted", 
        "message": "Full sync job (GitHub + Hardware) has been dispatched."
    }
