"""
L8 异动评分与分类作业 (17:30 盘后)
[v1.1 极简版 - 正式集成]
包含：异动分类 (E3)、评分溯源 (E3)、极端市况熔断 (E4)、D 视图生成 (E4)
"""
import asyncio
import logging
import sys
import os
import argparse
import json
from datetime import date, datetime
from typing import List, Dict, Any

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database.session import init_database, get_session
from services.anomaly.anomaly_scoring_service import anomaly_scoring_service
from services.anomaly.market_gating_service import market_gating_service
from services.anomaly.market_brief_service import market_brief_service
from adapters.stock_data_provider import data_provider
from database.anomaly_models import AnomalySignalModel
from sqlalchemy import select, and_

logger = logging.getLogger("AnomalyScoringJob")

async def run_anomaly_scoring_flow(target_date: date = None):
    """
    执行 17:30 异动评分管线
    """
    target_date = target_date or date.today()
    date_str = target_date.strftime("%Y-%m-%d")
    
    logger.info(f"🚀 Starting Anomaly Scoring Flow for {date_str}...")
    
    # 1. 初始化
    try:
        await init_database()
        await data_provider.initialize()
        await anomaly_scoring_service.initialize()
        await market_gating_service.initialize()
        await market_brief_service.initialize()
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        return
    
    # 2. 获取候选池 (L8 预筛选出的异动股)
    try:
        candidates = await data_provider.fetch_anomaly_candidates(target_date)
        if not candidates:
            logger.info("No anomaly candidates found for today. Skipping.")
            return
        
        # 3. 极端市况检查 (E4-S1)
        is_extreme, extreme_reason = await market_gating_service.check_extreme_market(target_date)
        if is_extreme:
            logger.warning(f"⚠️ Extreme Market Condition Detected: {extreme_reason}. Switching to D-View strategy.")
            is_push_allowed = False
        else:
            is_push_allowed = True
            
        logger.info(f"Found {len(candidates)} candidates. Enhancing features...")
        
        # 4. 增强特征数据 (LHB/公告等用于分类)
        ts_codes = [c["ts_code"] for c in candidates]
        features_map = await data_provider.get_anomaly_features_batch(ts_codes, target_date)
        
        # 合并特征
        for c in candidates:
            code = c["ts_code"]
            f = features_map.get(code, {})
            c["has_event"] = f.get("has_event", False)
            c["has_lhb"] = f.get("has_lhb", False)
            
        # 5. 执行评分与分类
        logger.info("Scoring and classifying stocks...")
        results = await anomaly_scoring_service.batch_score_stocks(candidates)
        
        # 6. 持久化到数据库
        await save_results_to_db(results, target_date, is_push_allowed)
        
        if not is_push_allowed:
            # 触发 E4-S3 D 视图生成
            logger.info("Generating D-View (app_market_brief)...")
            await market_brief_service.generate_market_brief(target_date)
            
        logger.info(f"✅ Anomaly Scoring Flow completed. Processed {len(results)} stocks. Push Allowed: {is_push_allowed}")
        
        # 输出统计信息供 Orchestrator
        output = {
            "date": date_str,
            "processed_count": len(results),
            "categories": {
                "C1": len([r for r in results if r.get("anomaly_category") == "C1"]),
                "C2": len([r for r in results if r.get("anomaly_category") == "C2"]),
                "C3": len([r for r in results if r.get("anomaly_category") == "C3"]),
                "C4": len([r for r in results if r.get("anomaly_category") == "C4"]),
            }
        }
        print(f"\n---GSD_START---\nGSD_OUTPUT_JSON: {json.dumps(output)}\n---GSD_END---", flush=True)

    except Exception as e:
        logger.error(f"Flow execution failed: {e}", exc_info=True)
        sys.exit(1)

async def save_results_to_db(results: List[Dict[str, Any]], target_date: date, is_push_allowed: bool):
    """
    保存结果到 MySQL (ads_l8_unified_signal)
    """
    async for session in get_session():
        try:
            from sqlalchemy.dialects.mysql import insert
            
            for res in results:
                # 构造插入数据
                # 如果是极端市况，强制 is_pushed = 0
                push_status = 0 if not is_push_allowed else 0 # 默认为 0，等待决策引擎捞取后置 1
                
                stmt = insert(AnomalySignalModel).values(
                    ts_code=res["ts_code"],
                    trade_date=target_date,
                    signal_type="L8_ANOMALY",
                    composite_score=res["anomaly_score"] if "anomaly_score" in res else res.get("composite_score", 0),
                    anomaly_category=res["anomaly_category"],
                    component_score=res["component_score"],  # JSON 字符串
                    source_version="v1.1",
                    is_pushed=push_status
                )
                
                # ON DUPLICATE KEY UPDATE
                update_stmt = stmt.on_duplicate_key_update(
                    composite_score=stmt.inserted.composite_score,
                    anomaly_category=stmt.inserted.anomaly_category,
                    component_score=stmt.inserted.component_score,
                    updated_at=datetime.now()
                )
                
                await session.execute(update_stmt)
            
            await session.commit()
            logger.info(f"Saved {len(results)} results to ads_l8_unified_signal.")
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to save results: {e}")
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="L8 异动评分与分类作业")
    parser.add_argument("--date", type=str, help="作业日期 (YYYY-MM-DD)")
    args = parser.parse_args()
    
    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    
    # 强制 Asia/Shanghai 时区逻辑 (AGENTS.md)
    asyncio.run(run_anomaly_scoring_flow(target_date))
