import asyncio
import json
import logging
import yaml
from enum import Enum
from typing import List, Optional, Dict, Set
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import akshare as ak
import pandas as pd
from pydantic import BaseModel
import fnmatch
from services.stock_pool.hot_sectors_manager import HotSectorsManager
from services.stock_pool.dynamic_pool_manager import DynamicPoolManager

logger = logging.getLogger(__name__)

class PoolLevel(Enum):
    L1_CORE = "L1_CORE"       # 核心池 (3秒/次)
    L2_ACTIVE = "L2_ACTIVE"   # 活跃池 (15秒/次)
    L3_UNIVERSE = "L3_UNIVERSE" # 全市场 (1分钟/次)

class StockPoolConfig(BaseModel):
    name: str
    level: PoolLevel
    symbols: Set[str]
    last_update: datetime

class StockPoolManager:
    """
    股票池管理器
    负责维护不同层级的股票列表
    
    Version 2.0: 增加按成交额Top 100和缓存降级功能
    """
    
    def __init__(self, cache_dir: str = "cache/stock_pools", config_manager=None):
        self.pools: Dict[PoolLevel, StockPoolConfig] = {
            PoolLevel.L1_CORE: StockPoolConfig(
                name="Core Assets", 
                level=PoolLevel.L1_CORE, 
                symbols=set(), 
                last_update=datetime.min
            ),
            PoolLevel.L2_ACTIVE: StockPoolConfig(
                name="Active Assets", 
                level=PoolLevel.L2_ACTIVE, 
                symbols=set(), 
                last_update=datetime.min
            ),
            PoolLevel.L3_UNIVERSE: StockPoolConfig(
                name="Market Universe", 
                level=PoolLevel.L3_UNIVERSE, 
                symbols=set(), 
                last_update=datetime.min
            )
        }
        
        # 缓存配置
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用ConfigManager（如果提供），否则使用旧的内联配置
        self.config_manager = config_manager
        
        # Initialize HotSectorsManager
        self.hot_sectors_manager = HotSectorsManager(config_manager) if config_manager else None
        
        # Initialize DynamicPoolManager for promoted stocks (Story 004.03)
        self.dynamic_pool = DynamicPoolManager(max_dynamic_size=20)
        
        # US-004.04: Dynamic pool size limit (controlled by AutoScaler)
        self.max_pool_size = 100  # Initial capacity
        
        # Backward compatible: use old inline config if no ConfigManager
        if not self.config_manager:
            self.config_path = Path("config/stock_pools.yaml")
            self.blacklist_enabled = False
            self.blacklist_patterns = []
            self.blacklist_codes = []
            self._load_blacklist_config()
    
    def _load_blacklist_config(self):
        """加载黑名单配置"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    
                blacklist_config = config.get('blacklist', {})
                self.blacklist_enabled = blacklist_config.get('enabled', False)
                self.blacklist_patterns = blacklist_config.get('patterns', [])
                self.blacklist_codes = blacklist_config.get('codes', [])
                
                if self.blacklist_enabled:
                    logger.info(f"✅ 黑名单已启用: {len(self.blacklist_patterns)} 个模式, {len(self.blacklist_codes)} 个代码")
                    logger.info(f"   过滤模式: {self.blacklist_patterns}")
                else:
                    logger.info("ℹ️ 黑名单未启用")
            else:
                logger.warning(f"⚠️ 配置文件不存在: {self.config_path}")
        except Exception as e:
            logger.error(f"❌ 加载黑名单配置失败: {e}")
    
    def _is_blacklisted(self, code: str, name: str) -> bool:
        """检查股票是否在黑名单中"""
        if not self.blacklist_enabled:
            return False
        
        # 检查代码黑名单
        if code in self.blacklist_codes:
            return True
        
        # 检查模式匹配
        for pattern in self.blacklist_patterns:
            # 匹配股票代码
            if fnmatch.fnmatch(code, pattern):
                return True
            # 匹配股票名称
            if fnmatch.fnmatch(name, pattern):
                return True
        
        return False
    
    def _is_blacklisted_via_manager(self, code: str, name: str) -> bool:
        """
        通过ConfigManager检查黑名单（新方式）
        
        Args:
            code: 股票代码
            name: 股票名称
            
        Returns:
            bool: True表示在黑名单中
        """
        if self.config_manager:
            return self.config_manager.is_blacklisted(code, {"名称": name})
        else:
            # 降级到旧方式
            return self._is_blacklisted(code, name)
    
    async def get_current_pool(self) -> List[str]:
        """
        获取当前激活的股票池 (支持模式切换和动态晋升)
        Story 004.02: Support switching between HS300 and Hot Sectors
        Story 004.03: Include dynamically promoted stocks
        """
        # 1. Get core pool based on mode
        if not self.config_manager:
            # Fallback to legacy behavior
            core_pool = await self.get_hs300_top100_by_volume()
        else:
            mode = self.config_manager.get_active_mode()
            logger.info(f"Fetching stock pool for mode: {mode}")
            
            if mode == "hs300_top100":
                core_pool = await self.get_hs300_top100_by_volume()
            elif mode == "hot_sectors":
                if self.hot_sectors_manager:
                    core_pool = await self.hot_sectors_manager.get_pool()
                else:
                    logger.error("HotSectorsManager not initialized")
                    core_pool = []
            elif mode == "custom":
                # Story 004.05: Custom pool support
                custom_config = self.config_manager.get_config().get("custom", {})
                groups = custom_config.get("groups", [])
                core_pool = groups[0].get("codes", []) if groups else []
            else:
                logger.warning(f"Unknown mode {mode}, falling back to HS300")
                core_pool = await self.get_hs300_top100_by_volume()
        
        # 2. Get dynamically promoted stocks (Story 004.03)
        promoted_stocks = await self.dynamic_pool.get_all_dynamic_stocks()
        
        if promoted_stocks:
            logger.info(f"🚀 Including {len(promoted_stocks)} promoted stocks in pool")
        
        # 3. Merge: promoted stocks first (priority), then core pool
        # Use dict.fromkeys to preserve order and deduplicate
        full_pool = list(dict.fromkeys(promoted_stocks + core_pool))
        
        # US-004.04: Limit pool size based on max_pool_size
        if len(full_pool) > self.max_pool_size:
            logger.info(f"📊 Limiting pool from {len(full_pool)} to {self.max_pool_size}")
            full_pool = full_pool[:self.max_pool_size]
        
        return full_pool

    async def get_hs300_top100_by_volume(self, lookback_days: int = 5) -> List[str]:
        """
        获取沪深300成分股按最近N日平均成交额Top 100
        Story 004.01 Implementation
        
        Args:
            lookback_days: 成交额回看天数，默认5天
            
        Returns:
            List[str]: 股票代码列表（100只）
        """

        logger.info(f"🔄 Fetching HS300 Top 100 by {lookback_days}-day avg volume...")
        
        try:
            # 0. 优先尝试加载今日缓存 (Optimization)
            today_str = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")
            cached = await self._load_pool_cache("hs300_top100")
            if cached:
                # Check if it's from today (by checking file metadata or content if available, 
                # but _load_pool_cache log says "Using cache from ...")
                # Since _load_pool_cache loads the LATEST, we just need to verify if we want to skip fetch.
                # For resilience, if we have RECENT cache (e.g. < 12 hours), we might skip.
                # But here, let's just rely on if it exists and is today.
                # The _load_pool_cache already logs age.
                # We need to know if it matches today to skip fetch.
                # Simplification: Let's trust _load_pool_cache returns valid data.
                # But we only want to skip fetch if it's TODAY's data.
                # We can't easily check date from returned list.
                # Let's peek at the file in check.
                pass 
                
            # Better implementation:
            # Check if today's cache file exists
            cache_file = self.cache_dir / f"hs300_top100_{today_str}.json"
            if cache_file.exists():
                logger.info(f"✅ Found today's cache {cache_file}, skipping fetch")
                return await self._load_pool_cache("hs300_top100")

            # 1. 获取沪深300成分股 (Run in thread pool)
            df_cons = await asyncio.to_thread(ak.index_stock_cons, symbol="000300")
            
            if df_cons is None or df_cons.empty:
                logger.error("Failed to fetch HS300 constituents")
                return await self._load_pool_cache("hs300_top100")
            
            logger.info(f"Fetched {len(df_cons)} HS300 constituents")
            
            # 2. 获取每只股票的平均成交额
            stock_volumes = []
            codes = df_cons['品种代码'].tolist()
            
            for i, code in enumerate(codes):
                try:
                    avg_amount = await self._get_avg_volume(code, lookback_days)
                    stock_volumes.append({
                        "code": code,
                        "name": df_cons[df_cons['品种代码'] == code]['品种名称'].iloc[0],
                        "avg_amount": avg_amount
                    })
                    
                    # 避免请求过快
                    if i % 10 == 0:
                        logger.info(f"Progress: {i}/{len(codes)} stocks processed")
                        await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Failed to get volume for {code}: {e}")
                    continue
            
            if not stock_volumes:
                logger.error("No stock volumes fetched, using cache")
                return await self._load_pool_cache("hs300_top100")
            
            # 3. 应用黑名单过滤（优先使用ConfigManager）
            blacklist_check = (
                self._is_blacklisted_via_manager 
                if self.config_manager 
                else lambda code, name: self._is_blacklisted(code, name)
            )
            
            # 检查是否启用黑名单
            blacklist_enabled = (
                self.config_manager.config.get("blacklist", {}).get("enabled", False)
                if self.config_manager
                else self.blacklist_enabled
            )
            
            if blacklist_enabled:
                before_filter = len(stock_volumes)
                stock_volumes = [
                    s for s in stock_volumes 
                    if not blacklist_check(s["code"], s["name"])
                ]
                filtered_count = before_filter - len(stock_volumes)
                if filtered_count > 0:
                    logger.info(f"🚫 黑名单过滤: 移除 {filtered_count} 只股票")
            
            # 4. 排序并取Top 100
            sorted_stocks = sorted(
                stock_volumes, 
                key=lambda x: x["avg_amount"], 
                reverse=True
            )[:100]
            
            logger.info(f"✅ Selected Top 100 stocks by volume")
            
            # 5. 保存缓存
            await self._save_pool_cache(sorted_stocks, "hs300_top100")
            
            # 6. 清理旧缓存
            await self._cleanup_old_caches("hs300_top100", max_age_days=7)
            
            return [s["code"] for s in sorted_stocks]
            
        except Exception as e:
            logger.error(f"Error getting HS300 Top100: {e}, falling back to cache")
            return await self._load_pool_cache("hs300_top100")
    
    async def _get_avg_volume(self, code: str, days: int) -> float:
        """
        获取股票最近N日平均成交额
        
        Args:
            code: 股票代码
            days: 回看天数
            
        Returns:
            float: 平均成交额（元）
        """
        try:
            # 计算日期范围
            end_date = datetime.now(ZoneInfo("Asia/Shanghai"))
            start_date = end_date - timedelta(days=days + 5)  # 多取几天，防止节假日
            
            # 获取历史数据 (Run in thread pool to avoid blocking event loop)
            df = await asyncio.to_thread(
                ak.stock_zh_a_hist,
                symbol=code,
                period="daily",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust=""
            )
            
            if df is None or df.empty:
                logger.warning(f"No data for {code}")
                return 0.0
            
            # 取最近N天的数据
            recent_data = df.tail(days)
            
            # 计算平均成交额
            avg_amount = recent_data['成交额'].mean() if '成交额' in recent_data.columns else 0.0
            
            return float(avg_amount)
            
        except Exception as e:
            logger.warning(f"Error getting volume for {code}: {e}")
            return 0.0
    
    async def _save_pool_cache(self, stocks: List[dict], pool_name: str):
        """
        保存股票池到缓存
        
        Args:
            stocks: 股票列表（包含code, name, avg_amount）
            pool_name: 池名称（如 "hs300_top100"）
        """
        try:
            now = datetime.now(ZoneInfo("Asia/Shanghai"))
            cache_file = self.cache_dir / f"{pool_name}_{now.strftime('%Y%m%d')}.json"
            
            cache_data = {
                "updated_at": now.isoformat(),
                "pool_name": pool_name,
                "count": len(stocks),
                "stocks": stocks
            }
            
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Cache saved: {cache_file}")
            
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    async def _load_pool_cache(self, pool_name: str) -> List[str]:
        """
        从缓存加载股票池（降级方案）
        
        Args:
            pool_name: 池名称
            
        Returns:
            List[str]: 股票代码列表
        """
        try:
            # 查找最新的缓存文件
            cache_files = sorted(
                self.cache_dir.glob(f"{pool_name}_*.json"),
                reverse=True
            )
            
            if not cache_files:
                logger.error(f"No cache found for {pool_name}")
                return []
            
            cache_file = cache_files[0]
            
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            # 检查缓存年龄 - 确保时区一致性
            cached_time = datetime.fromisoformat(cache_data["updated_at"])
            # 如果缓存时间没有时区信息，添加Asia/Shanghai时区
            if cached_time.tzinfo is None:
                cached_time = cached_time.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
            
            now = datetime.now(ZoneInfo("Asia/Shanghai"))
            age_days = (now - cached_time).days
            
            if age_days > 7:
                logger.error(f"⚠️ Cache is {age_days} days old (> 7 days limit)")
            elif age_days > 3:
                logger.warning(f"⚠️ Cache is {age_days} days old")
            else:
                logger.info(f"📂 Using cache from {cached_time.date()} ({age_days} days old)")
            
            stocks = cache_data["stocks"]
            return [s["code"] for s in stocks]
            
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            return []
    
    async def _cleanup_old_caches(self, pool_name: str, max_age_days: int = 7):
        """
        清理超过指定天数的缓存文件
        
        Args:
            pool_name: 池名称
            max_age_days: 最大保留天数
        """
        try:
            cache_files = list(self.cache_dir.glob(f"{pool_name}_*.json"))
            now = datetime.now(ZoneInfo("Asia/Shanghai"))
            
            for cache_file in cache_files:
                try:
                    # 从文件名提取日期
                    date_str = cache_file.stem.split("_")[-1]
                    file_date = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                    age_days = (now - file_date).days
                    
                    if age_days > max_age_days:
                        cache_file.unlink()
                        logger.info(f"🗑️ Deleted old cache: {cache_file.name} ({age_days} days old)")
                        
                except Exception as e:
                    logger.warning(f"Error processing cache file {cache_file}: {e}")
            
        except Exception as e:
            logger.error(f"Error cleaning up caches: {e}")
    
    # ========== 原有方法（保持兼容性） ==========
    
    def initialize_static_l1_pool(self) -> int:
        """
        初始化静态L1池 (沪深300全部成分股)
        
        注意：此方法保留用于向后兼容，新代码请使用 get_hs300_top100_by_volume()
        
        Returns:
            int: 池中股票数量
        """
        print("🔄 Initializing Static L1 Pool (CSI 300)...")
        try:
            df = ak.index_stock_cons(symbol="000300")
            
            if df is None or df.empty:
                print("⚠️ Failed to fetch CSI 300 data")
                return 0
            
            symbols = set(df['品种代码'].tolist())
            
            self.pools[PoolLevel.L1_CORE].symbols = symbols
            self.pools[PoolLevel.L1_CORE].last_update = datetime.now()
            
            print(f"✅ L1 Pool Initialized: {len(symbols)} stocks")
            return len(symbols)
            
        except Exception as e:
            print(f"❌ Error initializing L1 pool: {e}")
            return 0

    def get_pool_symbols(self, level: PoolLevel) -> List[str]:
        """获取指定池的股票列表"""
        return list(self.pools[level].symbols)

    def add_custom_to_l1(self, symbols: List[str]):
        """添加自选股到L1池"""
        current = self.pools[PoolLevel.L1_CORE].symbols
        current.update(symbols)
        self.pools[PoolLevel.L1_CORE].symbols = current
        print(f"➕ Added {len(symbols)} custom stocks to L1. Total: {len(current)}")

if __name__ == "__main__":
    # 测试代码
    async def test():
        manager = StockPoolManager()
        
        # 测试新功能：获取Top 100
        stocks = await manager.get_hs300_top100_by_volume(lookback_days=5)
        print(f"✅ Got {len(stocks)} stocks")
        print(f"Sample: {stocks[:5]}")
        
        # 测试缓存加载
        cached_stocks = await manager._load_pool_cache("hs300_top100")
        print(f"📂 Cache has {len(cached_stocks)} stocks")
    
    asyncio.run(test())
