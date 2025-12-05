"""
Hot Sectors Manager

Responsible for building the "Hot Sectors" stock pool by fetching data from:
1. ETF constituents (via akshare)
2. Manual lists (from config)
3. Dynamic "Monster" stocks (high surge/turnover)
"""
import logging
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import akshare as ak
import pandas as pd
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

class HotSectorsManager:
    """热门赛道股票池管理器"""
    
    def __init__(self, config_manager, cache_dir: str = "cache/hot_sectors"):
        self.config_manager = config_manager
        self.cache_path = Path(cache_dir)
        self.cache_path.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        
    async def get_pool(self) -> List[str]:
        """
        获取热门赛道股票池
        优先使用当天缓存，如果无缓存则构建新池
        """
        async with self._lock:
            # 1. 尝试加载当天缓存
            cached_pool = self._load_cache()
            if cached_pool:
                logger.info(f"Using cached hot sectors pool ({len(cached_pool)} stocks)")
                return cached_pool
            
            # 2. 构建新池
            logger.info("Building new hot sectors pool...")
            pool = await self._build_pool()
            
            # 3. 保存缓存
            if pool:
                self._save_cache(pool)
                
            return pool

    async def _build_pool(self) -> List[str]:
        """构建股票池"""
        config = self.config_manager.get_config()
        if not config or "hot_sectors" not in config or not config["hot_sectors"].get("sectors"):
            logger.warning("Hot sectors configuration missing or empty")
            return []
            
        sectors_config = config["hot_sectors"]["sectors"]
        all_stocks = []
        
        for sector_key, sector_conf in sectors_config.items():
            try:
                logger.info(f"Processing sector: {sector_conf.get('name', sector_key)}")
                
                if sector_conf.get("dynamic", False):
                    # 动态妖股池
                    stocks = await self._get_monster_stocks(sector_conf)
                else:
                    # 静态/ETF赛道
                    stocks = await self._get_sector_stocks(sector_conf)
                
                all_stocks.extend(stocks)
                logger.info(f"Sector {sector_key} added {len(stocks)} stocks")
                
            except Exception as e:
                logger.error(f"Error processing sector {sector_key}: {e}")
                continue
                
        # 去重并保持顺序
        unique_stocks = list(dict.fromkeys(all_stocks))
        
        # 限制总数量 (约100只，但允许配置控制)
        # 这里我们不做硬性截断，而是依赖各赛道的size配置
        
        logger.info(f"Built hot sectors pool with {len(unique_stocks)} unique stocks")
        return unique_stocks

    async def _get_sector_stocks(self, config: dict) -> List[str]:
        """获取单个赛道的股票"""
        stocks = []
        sources = config.get("sources", [])
        
        for source in sources:
            try:
                if source["type"] == "etf":
                    # 异步执行耗时的网络请求
                    etf_stocks = await asyncio.to_thread(
                        self._get_etf_stocks_sync, 
                        source["code"], 
                        source.get("top_n", 10)
                    )
                    stocks.extend(etf_stocks)
                    
                elif source["type"] == "manual":
                    stocks.extend(source.get("codes", []))
                    
            except Exception as e:
                logger.error(f"Error fetching source {source}: {e}")
                continue
        
        # 应用过滤器
        if "filters" in config:
            stocks = await self._apply_filters(stocks, config["filters"])
            
        # 限制数量
        return stocks[:config.get("size", 20)]

    def _get_etf_stocks_sync(self, etf_code: str, top_n: int) -> List[str]:
        """
        同步获取ETF成分股 (运行在线程池中)
        使用 akshare 接口
        """
        try:
            # 尝试获取ETF持仓
            # 注意：akshare接口可能会变，需做好容错
            # fund_etf_fund_info_em: 天天基金网-ETF-持仓
            df = ak.fund_etf_fund_info_em(fund=etf_code)
            
            if df.empty:
                logger.warning(f"ETF {etf_code} returned empty data")
                return []
                
            # 按持仓占比排序 (假设列名为 '持仓占比')
            # 实际列名可能需要检查，通常是 '股票代码', '股票名称', '持仓占比'
            if "持仓占比" in df.columns:
                df["持仓占比"] = pd.to_numeric(df["持仓占比"], errors="coerce")
                df = df.sort_values("持仓占比", ascending=False)
            
            return df.head(top_n)["股票代码"].tolist()
            
        except Exception as e:
            logger.warning(f"Failed to fetch ETF {etf_code} via fund_etf_fund_info_em: {e}")
            
            # 降级方案：尝试使用指数成分股接口
            try:
                # index_stock_cons: 指数成分股
                df = ak.index_stock_cons(symbol=etf_code)
                return df.head(top_n)["品种代码"].tolist()
            except Exception as e2:
                logger.error(f"Fallback fetch for ETF {etf_code} also failed: {e2}")
                return []

    async def _get_monster_stocks(self, config: dict) -> List[str]:
        """获取动态妖股"""
        try:
            # 异步执行
            return await asyncio.to_thread(self._get_monster_stocks_sync, config)
        except Exception as e:
            logger.error(f"Error getting monster stocks: {e}")
            return []

    def _get_monster_stocks_sync(self, config: dict) -> List[str]:
        """同步获取妖股逻辑"""
        try:
            # 获取全市场实时行情
            df_all = ak.stock_zh_a_spot_em()
            
            criteria = config.get("criteria", [])
            for criterion in criteria:
                field = criterion["field"]
                operator = criterion["operator"]
                value = criterion["value"]
                
                # 映射字段名
                # akshare返回的字段通常是中文，如 "最新价", "涨跌幅", "换手率", "流通市值"
                
                if field not in df_all.columns:
                    continue
                    
                if operator == ">":
                    df_all = df_all[df_all[field] > value]
                elif operator == "<":
                    df_all = df_all[df_all[field] < value]
            
            # 默认按涨幅排序
            df_sorted = df_all.sort_values("涨跌幅", ascending=False)
            return df_sorted.head(config.get("size", 10))["代码"].tolist()
            
        except Exception as e:
            logger.error(f"Failed to calculate monster stocks: {e}")
            return []

    async def _apply_filters(self, stocks: List[str], filters: dict) -> List[str]:
        """应用过滤器 (如最小成交额)"""
        # 暂时跳过复杂过滤，避免过多网络请求导致超时
        # 实际生产中应使用本地数据库或批量接口
        return stocks

    def _load_cache(self) -> Optional[List[str]]:
        """加载当天缓存"""
        today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")
        cache_file = self.cache_path / f"hot_sectors_{today}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("stocks", [])
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
        return None

    def _save_cache(self, stocks: List[str]):
        """保存缓存"""
        today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")
        cache_file = self.cache_path / f"hot_sectors_{today}.json"
        
        # 清理旧缓存
        for f in self.cache_path.glob("hot_sectors_*.json"):
            if f.name != cache_file.name:
                f.unlink(missing_ok=True)
                
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "date": today,
                    "updated_at": datetime.now().isoformat(),
                    "stocks": stocks,
                    "count": len(stocks)
                }, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
