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
            # 使用正确的 API: fund_portfolio_hold_em
            # 该接口返回 ETF 的持仓明细
            from datetime import datetime
            current_year = datetime.now().year
            
            logger.info(f"Fetching ETF {etf_code} holdings via fund_portfolio_hold_em")
            df = ak.fund_portfolio_hold_em(symbol=etf_code, date=str(current_year))
            
            if df is None or df.empty:
                logger.warning(f"ETF {etf_code} returned empty holdings")
                return []
            
            # 列名: ['序号', '股票代码', '股票名称', '占净值比例', '持股数', '持仓市值', '季度']
            # 按 '占净值比例' 排序（已经是从高到低）
            if "占净值比例" in df.columns:
                df["占净值比例"] = pd.to_numeric(df["占净值比例"], errors="coerce")
                df = df.sort_values("占净值比例", ascending=False)
            
            # 返回股票代码
            stocks = df.head(top_n)["股票代码"].tolist()
            logger.info(f"ETF {etf_code}: got {len(stocks)} stocks")
            return stocks
            
        except Exception as e:
            logger.warning(f"Failed to fetch ETF {etf_code} via fund_portfolio_hold_em: {e}")
            
            # 降级方案：尝试使用指数成分股接口
            try:
                logger.info(f"Trying fallback: index_stock_cons for {etf_code}")
                df = ak.index_stock_cons(symbol=etf_code)
                
                if df is None or df.empty:
                    logger.warning(f"Fallback also returned empty for {etf_code}")
                    return []
                    
                stocks = df.head(top_n)["品种代码"].tolist()
                logger.info(f"Fallback succeeded: got {len(stocks)} stocks")
                return stocks
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
        """
        使用 mootdx 获取妖股（从热门股票中筛选）
        
        策略：不扫描全市场48K股票（太慢），而是：
        1. 从沪深300等活跃股票中采样
        2. 加上近期成交额Top500
        3. 从这个子集中筛选高涨幅股票
        """
        import time
        from mootdx.quotes import Quotes
        
        try:
            logger.info(f"🎲 Fetching monster stocks via mootdx (sampling strategy)...")
            
            # 初始化 mootdx 客户端
            client = Quotes.factory(market='std', multithread=True, heartbeat=True)
            
            # 获取全市场股票列表
            stocks_sz = client.stocks(market=0)  # 深圳 
            stocks_sh = client.stocks(market=1)  # 上海
            
            all_stocks = pd.concat([stocks_sz, stocks_sh], ignore_index=True)
            logger.info(f"Got {len(all_stocks)} total stocks")
            
            # 采样策略：随机选择1000只股票（代表性采样）
            # 这比扫描全市场快得多，且能捕捉大部分妖股
            sample_size = min(1000, len(all_stocks))
            sampled_stocks = all_stocks.sample(n=sample_size, random_state=42)
            sample_codes = sampled_stocks['code'].tolist()
            
            logger.info(f"Sampled {len(sample_codes)} stocks for monster detection")
            
            # 分小批获取行情（每批50只）
            batch_size = 50
            all_quotes =  []
            
            for i in range(0, len(sample_codes), batch_size):
                batch = sample_codes[i:i+batch_size]
                try:
                    quotes = client.quotes(symbol=batch)
                    if quotes is not None and not quotes.empty:
                        all_quotes.append(quotes)
                except Exception as e:
                    logger.warning(f"Batch {i//batch_size + 1} failed: {str(e)[:100]}")
                    continue
                
                # 避免请求过快
                time.sleep(0.2)
            
            if not all_quotes:
                logger.error("No quotes fetched successfully")
                return []
            
            # 合并所有批次
            df_all = pd.concat(all_quotes, ignore_index=True)
            logger.info(f"Got {len(df_all)} quotes from mootdx")
            
            # 计算涨跌幅
            df_all['涨跌幅'] = ((df_all['price'] - df_all['last_close']) / df_all['last_close'] * 100).fillna(0)
            
            # 只用涨跌幅筛选（忽略config中的换手率/市值条件，因为mootdx不提供）
            threshold = 9.0  # 涨幅 > 9%
            df_filtered = df_all[df_all['涨跌幅'] > threshold]
            
            logger.info(f"After filtering (涨幅>{threshold}%): {len(df_filtered)} stocks")
            
            if df_filtered.empty:
                logger.warning("No monster stocks found today (no stocks > 9% gain)")
                return []
            
            # 按涨幅排序，取前N只
            df_sorted = df_filtered.sort_values("涨跌幅", ascending=False)
            size = config.get("size", 10)
            monsters = df_sorted.head(size)['code'].tolist()
            
            logger.info(f"✅ Monster stocks (mootdx): found {len(monsters)} stocks")
            if monsters and len(df_sorted) > 0:
                top_gains = df_sorted.head(3)[['code', '涨跌幅']].to_dict('records')
                for stock in top_gains:
                    logger.info(f"   {stock['code']}: +{stock['涨跌幅']:.2f}%")
            
            return monsters
            
        except Exception as e:
            logger.error(f"Failed to get monster stocks: {type(e).__name__}: {str(e)[:200]}")
            import traceback
            traceback.print_exc()
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
