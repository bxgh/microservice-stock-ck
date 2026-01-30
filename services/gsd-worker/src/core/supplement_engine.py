import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import pytz
import asynch
import os

from core.tick_sync_service import TickSyncService
from core.sync_service import KLineSyncService
from collectors.financial_collector import FinancialCollector
from collectors.capital_flow_collector import CapitalFlowCollector
from collectors.valuation_collector import ValuationCollector
from collectors.top_list_collector import TopListCollector
from collectors.dividend_collector import DividendCollector
from collectors.block_trade_collector import BlockTradeCollector
from collectors.margin_collector import MarginCollector
from collectors.shareholder_collector import ShareholderCollector

# Shanghai timezone
CST = pytz.timezone('Asia/Shanghai')

logger = logging.getLogger(__name__)

class DataSupplementEngine:
    """
    Data Supplement Engine Core Class
    """
    
    def __init__(self):
        self.tick_service: Optional[TickSyncService] = None
        self.kline_service: Optional[KLineSyncService] = None
        
        # Cloud collectors
        self.financial_collector: Optional[FinancialCollector] = None
        self.capital_flow_collector: Optional[CapitalFlowCollector] = None
        self.valuation_collector: Optional[ValuationCollector] = None
        self.top_list_collector: Optional[TopListCollector] = None
        self.dividend_collector: Optional[DividendCollector] = None
        self.block_trade_collector: Optional[BlockTradeCollector] = None
        self.margin_collector: Optional[MarginCollector] = None
        self.shareholder_collector: Optional[ShareholderCollector] = None
        
        self.ch_pool = None
        self._initialized = False

    async def initialize(self):
        """Initialize all collector services"""
        if self._initialized:
            return

        logger.info("Initializing DataSupplementEngine...")
        
        # 0. Init Shared Pools
        self.ch_pool = await asynch.create_pool(
            host=os.getenv('CLICKHOUSE_HOST', 'localhost'),
            port=int(os.getenv('CLICKHOUSE_PORT', 9000)),
            user=os.getenv('CLICKHOUSE_USER', 'admin'),
            password=os.getenv('CLICKHOUSE_PASSWORD', 'admin123'),
            database=os.getenv('CLICKHOUSE_DB', 'stock_data')
        )
        
        # 1. Init Tick Service (Local/TDX)
        self.tick_service = TickSyncService()
        await self.tick_service.initialize()
        
        # 2. Init Kline Service (Cloud/API)
        self.kline_service = KLineSyncService()
        await self.kline_service.initialize()
        
        # 3. Init Cloud Collectors (Phase 4)
        self.financial_collector = FinancialCollector(self.ch_pool)
        await self.financial_collector.initialize()
        
        self.capital_flow_collector = CapitalFlowCollector(self.ch_pool)
        await self.capital_flow_collector.initialize()
        
        self.valuation_collector = ValuationCollector(self.ch_pool)
        await self.valuation_collector.initialize()
        
        self.top_list_collector = TopListCollector(self.ch_pool)
        await self.top_list_collector.initialize()
        
        self.dividend_collector = DividendCollector(self.ch_pool)
        await self.dividend_collector.initialize()
        
        self.block_trade_collector = BlockTradeCollector(self.ch_pool)
        await self.block_trade_collector.initialize()
        
        self.margin_collector = MarginCollector(self.ch_pool)
        await self.margin_collector.initialize()
        
        self.shareholder_collector = ShareholderCollector(self.ch_pool)
        await self.shareholder_collector.initialize()
        
        self._initialized = True
        logger.info("DataSupplementEngine initialized.")

    async def close(self):
        """Release resources"""
        if self.tick_service:
            await self.tick_service.close()
        if self.kline_service:
            await self.kline_service.close()
        
        # Close all cloud collectors
        collectors = [
            self.financial_collector,
            self.capital_flow_collector,
            self.valuation_collector,
            self.top_list_collector,
            self.dividend_collector,
            self.block_trade_collector,
            self.margin_collector,
            self.shareholder_collector
        ]
        
        for collector in collectors:
            if collector:
                await collector.close()
            
        # Close shared pool
        if self.ch_pool:
            self.ch_pool.close()
            await self.ch_pool.wait_closed()
        
        self._initialized = False
        logger.info("DataSupplementEngine closed.")

    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行补充任务"""
        # ... (same as original run method)
        if not self._initialized:
            raise RuntimeError("Engine not initialized. Call initialize() first.")

        stocks = params.get("stocks", [])
        if not stocks:
            logger.warning("No stocks provided for supplement task.")
            return {"status": "skipped", "reason": "empty_stocks"}

        # 解析日期
        date_list = self._parse_dates(params)
        
        # 解析数据类型
        data_types = params.get("data_types", ["tick", "kline"])
        
        logger.info(f"Starting supplement task: {len(stocks)} stocks, {len(date_list)} dates, types={data_types}")
        
        results = {
            "total_stocks": len(stocks),
            "processed_dates": len(date_list),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }

        # 执行并发处理
        concurrency = params.get("concurrency_override", 5)
        semaphore = asyncio.Semaphore(concurrency)
        
        async def _worker(code):
            async with semaphore:
                return await self._process_stock(code, date_list, data_types)

        logger.info(f"🚀 并发执行补充任务: 总数={len(stocks)}, 并发={concurrency}")
        
        tasks = [_worker(code) for code in stocks]
        total = len(stocks)
        processed = 0
        
        for f in asyncio.as_completed(tasks):
            stock_result = await f
            results["details"].append(stock_result)
            
            if stock_result["status"] in ("success", "partial"):
                results["success"] += 1
            else:
                results["failed"] += 1
            
            processed += 1
            if processed % 100 == 0 or processed == total:
                logger.info(f"📊 进度: {processed}/{total} ({(processed/total):.1%})")

        logger.info(f"✨ Supplement task completed. Success: {results['success']}, Failed: {results['failed']}")
        return results

    async def _process_stock(self, code: str, dates: List[str], data_types: List[str]) -> Dict[str, Any]:
        """处理单只股票"""
        result = {
            "code": code,
            "status": "pending",
            "type_results": {}
        }
        
        has_failure = False
        all_success = True
        
        for dtype in data_types:
            try:
                if dtype == "tick":
                    count = 0
                    for date_str in dates:
                        c = await self.tick_service.sync_stock(code, date_str)
                        if c >= 0:
                            count += c
                        else: 
                            has_failure = True
                            all_success = False
                    result["type_results"][dtype] = {"status": "success", "records": count}
                    
                elif dtype == "kline":
                    logger.warning(f"KLine supplement for {code} not fully implemented in Core Engine yet.")
                    result["type_results"][dtype] = {"status": "skipped", "reason": "not_implemented"}

                elif dtype == "financial":
                    # Financial is typically date-independent or latest, but can be history
                    # For now, collect once per stock (API behaves like snapshot/latest)
                    # Use first date if any, or None
                    c = await self.financial_collector.collect(code)
                    result["type_results"][dtype] = {"status": "success", "records": c}

                elif dtype == "capital_flow":
                    c = await self.capital_flow_collector.collect(code)
                    result["type_results"][dtype] = {"status": "success", "records": c}

                elif dtype == "valuation":
                    # Use first date if provided, otherwise collector uses current date
                    date_param = dates[0] if dates else None
                    c = await self.valuation_collector.collect(code, date_param)
                    result["type_results"][dtype] = {"status": "success", "records": c}

                elif dtype == "top_list":
                    # Top list is usually date-based, not stock-based, but we can filter
                    date_param = dates[0] if dates else None
                    c = await self.top_list_collector.collect(code, date_param)
                    result["type_results"][dtype] = {"status": "success", "records": c}

                elif dtype == "dividend":
                    c = await self.dividend_collector.collect(code)
                    result["type_results"][dtype] = {"status": "success", "records": c}

                elif dtype == "block_trade":
                    c = await self.block_trade_collector.collect(code)
                    result["type_results"][dtype] = {"status": "success", "records": c}

                elif dtype == "margin":
                    c = await self.margin_collector.collect(code)
                    result["type_results"][dtype] = {"status": "success", "records": c}

                elif dtype == "shareholder":
                    counts = await self.shareholder_collector.collect(code)
                    # Sum up the counts for reporting
                    total_records = counts["holder_count"] + counts["top_holders"]
                    result["type_results"][dtype] = {"status": "success", "records": total_records}

                else:
                    result["type_results"][dtype] = {"status": "skipped", "reason": "not_implemented"}
                    
            except Exception as e:
                logger.error(f"Error processing {code} - {dtype}: {e}")
                result["type_results"][dtype] = {"status": "failed", "error": str(e)}
                has_failure = True
                all_success = False


        if all_success:
            result["status"] = "success"
        elif has_failure:
             # 如果至少有一个成功，则是 partial
             # 这里简化，只要有失败且没全成功，就算 partial 或 failed
             pass 
             
        # 简单判定
        failed_count = sum(1 for v in result["type_results"].values() if v.get("status") == "failed")
        success_count = sum(1 for v in result["type_results"].values() if v.get("status") == "success")
        
        if failed_count == 0 and success_count > 0:
            result["status"] = "success"
        elif failed_count > 0 and success_count > 0:
             result["status"] = "partial"
        elif failed_count > 0:
            result["status"] = "failed"
        else:
            result["status"] = "skipped" # all skipped

        return result

    def _parse_dates(self, params: Dict[str, Any]) -> List[str]:
        """生成日期列表 (YYYYMMDD)"""
        # 1. 单日优先
        if params.get("date"):
            return [params["date"].replace("-", "")]
            
        # 2. 日期范围
        date_range = params.get("date_range")
        if date_range and "start" in date_range and "end" in date_range:
            start_str = date_range["start"].replace("-", "")
            end_str = date_range["end"].replace("-", "")
            # 生成日期序列 (仅交易日？暂且生成自然日，SyncService 会过滤非交易日)
            # 简单起见，暂时返回 [start, end] 范围内的所有日期字符串
            # 实际生产中应结合 Calendar
            from datetime import timedelta
            
            s_date = datetime.strptime(start_str, "%Y%m%d")
            e_date = datetime.strptime(end_str, "%Y%m%d")
            
            days = (e_date - s_date).days + 1
            res = []
            for i in range(days):
                d = s_date + timedelta(days=i)
                res.append(d.strftime("%Y%m%d"))
            return res
            
        # 3. 默认当日
        return [datetime.now(CST).strftime("%Y%m%d")]
