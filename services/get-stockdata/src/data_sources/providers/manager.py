# -*- coding: utf-8 -*-
"""
EPIC-007 数据服务管理器

统一的数据服务入口,提供:
1. 各类数据的统一获取接口
2. 自动数据源降级
3. 时段感知策略
4. 监控统计

@author: EPIC-007
@date: 2025-12-06
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from data_sources.providers import (
    DataProvider, DataResult, DataType, ProviderChain,
    MootdxProvider, EasyquotationProvider, AkshareProvider,
    PywencaiProvider, BaostockProvider,
)
from data_sources.strategy import TimeAwareStrategy, get_time_strategy

logger = logging.getLogger(__name__)


class DataServiceManager:
    """数据服务管理器
    
    统一管理所有数据源,提供简洁的 API 获取各类数据。
    
    Features:
    - 自动初始化和管理所有 Provider
    - 按数据类型组织 ProviderChain
    - 时段感知 (盘中/盘后不同策略)
    - 自动降级和熔断保护
    - 监控统计
    
    Example:
        # 初始化
        manager = DataServiceManager()
        await manager.initialize()
        
        # 获取实时行情
        result = await manager.get_quotes(codes=["000001", "600519"])
        print(result.data)
        
        # 获取涨停股票
        result = await manager.get_ranking(ranking_type="limit_up")
        
        # 自然语言选股
        result = await manager.screen("市值小于50亿的科技股")
        
        # 关闭
        await manager.close()
    """
    
    def __init__(
        self,
        config: Optional[Dict] = None,
        enable_circuit_breaker: bool = True,
        enable_time_aware: bool = True,
    ):
        """初始化
        
        Args:
            config: 自定义配置 (数据源优先级等)
            enable_circuit_breaker: 是否启用熔断器
            enable_time_aware: 是否启用时段感知策略
        """
        self._config = config or {}
        self._enable_circuit_breaker = enable_circuit_breaker
        self._enable_time_aware = enable_time_aware
        
        # 时段策略
        self._time_strategy = get_time_strategy() if enable_time_aware else None
        
        # Provider 实例
        self._providers: List[DataProvider] = []
        
        # ProviderChain 实例 (按数据类型)
        self._chains: Dict[DataType, ProviderChain] = {}
        
        # 状态
        self._initialized = False
        self._lock = asyncio.Lock()
        
        # 懒加载状态追踪
        self._initialized_providers = set()  # 已初始化的provider名称
        self._init_locks = {}  # 每个provider的初始化锁
    
    async def initialize(self) -> bool:
        """初始化数据源（混合策略：核心顺序+可选懒加载）
        
        Returns:
            bool: 是否成功
        """
        async with self._lock:
            if self._initialized:
                return True
            
            logger.info("=== Initializing DataServiceManager (Hybrid Strategy) ===")
            
            # 创建所有 Provider 实例（但不立即初始化）
            provider_instances = {
                'mootdx': MootdxProvider(),
                'akshare': AkshareProvider(),
                'easyquotation': EasyquotationProvider(),
                'pywencai': PywencaiProvider(),
            }
            
            # 可选: 添加 baostock
            if self._config.get("enable_baostock", True):  # 默认启用
                provider_instances['baostock'] = BaostockProvider()
            
            # 核心 provider（启动时顺序初始化）
            core_providers = ['mootdx', 'akshare']
            
            # 可选 provider（懒加载）
            optional_providers = ['easyquotation', 'pywencai']
            if 'baostock' in provider_instances:
                optional_providers.append('baostock')
            
            logger.info(f"Core providers: {core_providers}")
            logger.info(f"Optional providers (lazy-load): {optional_providers}")
            
            # === Phase 1: 顺序初始化核心 Provider ===
            logger.info("Phase 1: Initializing core providers sequentially...")
            init_results = {}
            
            for name in core_providers:
                provider = provider_instances[name]
                logger.info(f"Initializing {name}...")
                
                try:
                    success = await provider.initialize()
                    init_results[name] = success
                    
                    if success:
                        self._providers.append(provider)
                        self._initialized_providers.add(name)
                        logger.info(f"✅ {name} initialized successfully")
                    else:
                        logger.warning(f"⚠️ {name} initialization failed")
                    
                    # 延迟200ms，避免并发冲突
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"❌ {name} initialization error: {e}")
                    init_results[name] = False
            
            # === Phase 2: 准备可选 Provider（不初始化） ===
            logger.info("Phase 2: Registering optional providers for lazy-loading...")
            
            for name in optional_providers:
                provider = provider_instances[name]
                self._providers.append(provider)  # 添加到列表，但不初始化
                self._init_locks[name] = asyncio.Lock()  # 创建锁
                logger.info(f"📌 {name} registered (will be lazy-loaded on first use)")
            
            # 创建 ProviderChain
            logger.info("Creating provider chains...")
            for data_type in DataType:
                chain = ProviderChain(
                    providers=self._providers,
                    data_type=data_type,
                    enable_circuit_breaker=self._enable_circuit_breaker,
                )
                if chain.providers:
                    self._chains[data_type] = chain
                    logger.info(f"Chain {data_type.value}: {[p.name for p in chain.providers]}")
            
            self._initialized = True
            logger.info(f"\n✅ DataServiceManager initialized:")
            logger.info(f"   - Core providers ready: {list(self._initialized_providers)}")
            logger.info(f"   - Optional providers: {optional_providers}")
            logger.info(f"   - Total providers: {len(self._providers)}")
            return True
    
    async def _ensure_provider_initialized(self, provider_name: str) -> bool:
        """确保provider已初始化（懒加载+线程安全）
        
        Args:
            provider_name: provider名称
            
        Returns:
            bool: 是否成功初始化
        """
        # 快速路径：已初始化
        if provider_name in self._initialized_providers:
            return True
        
        # 核心provider应该已经初始化了
        if provider_name in ['mootdx', 'akshare']:
            logger.warning(f"{provider_name} should be initialized during startup")
            return provider_name in self._initialized_providers
        
        # 可选provider：懒加载
        if provider_name not in self._init_locks:
            logger.error(f"Unknown provider: {provider_name}")
            return False
        
        async with self._init_locks[provider_name]:
            # Double-check（避免重复初始化）
            if provider_name in self._initialized_providers:
                return True
            
            logger.info(f"🔄 Lazy-loading provider: {provider_name}...")
            
            try:
                # 找到provider实例
                provider = next((p for p in self._providers if p.name == provider_name), None)
                if not provider:
                    logger.error(f"Provider {provider_name} not found in providers list")
                    return False
                
                success = await provider.initialize()
                
                if success:
                    self._initialized_providers.add(provider_name)
                    logger.info(f"✅ {provider_name} lazy-loaded successfully")
                    return True
                else:
                    logger.warning(f"⚠️ {provider_name} initialization failed")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ {provider_name} lazy-load error: {e}")
                return False
    
    async def close(self) -> None:
        """关闭所有数据源"""
        async with self._lock:
            for provider in self._providers:
                try:
                    await provider.close()
                except Exception as e:
                    logger.error(f"Provider {provider.name} close error: {e}")
            
            self._providers.clear()
            self._chains.clear()
            self._initialized = False
            logger.info("DataServiceManager closed")
    
    def add_provider(self, provider: DataProvider) -> None:
        """添加自定义 Provider
        
        Args:
            provider: DataProvider 实例
        """
        self._providers.append(provider)
        logger.info(f"Added provider: {provider.name}")
        
        # 需要重建 chain
        for data_type in provider.capabilities:
            if data_type in self._chains:
                # 重建 chain
                self._chains[data_type] = ProviderChain(
                    providers=self._providers,
                    data_type=data_type,
                    enable_circuit_breaker=self._enable_circuit_breaker,
                )
    
    # ========== 数据获取 API ==========
    
    async def get_quotes(self, codes: List[str], **kwargs) -> DataResult:
        """获取实时行情
        
        Args:
            codes: 股票代码列表
        
        Returns:
            DataResult
        """
        chain = self._chains.get(DataType.QUOTES)
        if not chain:
            return DataResult(success=False, error="No provider for QUOTES")
        
        return await chain.fetch(codes=codes, **kwargs)
    
    async def get_tick(self, code: str, **kwargs) -> DataResult:
        """获取分笔成交数据
        
        Args:
            code: 股票代码
            start: 起始位置
            count: 数量
        """
        chain = self._chains.get(DataType.TICK)
        if not chain:
            return DataResult(success=False, error="No provider for TICK")
        
        return await chain.fetch(code=code, **kwargs)
    
    async def get_history(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        frequency: str = "d",
        **kwargs
    ) -> DataResult:
        """获取历史K线
        
        Args:
            code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期
            frequency: 周期 (d/w/m/5/15/30/60)
        """
        chain = self._chains.get(DataType.HISTORY)
        if not chain:
            return DataResult(success=False, error="No provider for HISTORY")
        
        return await chain.fetch(
            code=code,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
            **kwargs
        )
    
    async def get_ranking(
        self,
        ranking_type: str = "limit_up",
        date_str: Optional[str] = None,
        **kwargs
    ) -> DataResult:
        """获取榜单数据
        
        Args:
            ranking_type: 榜单类型
                - "hot": 人气榜
                - "surge": 飙升榜
                - "limit_up": 涨停池
                - "continuous_limit_up": 连板统计
                - "dragon_tiger": 龙虎榜
            date_str: 日期 (YYYYMMDD)
        """
        chain = self._chains.get(DataType.RANKING)
        if not chain:
            return DataResult(success=False, error="No provider for RANKING")
        
        return await chain.fetch(
            ranking_type=ranking_type,
            date_str=date_str,
            **kwargs
        )
    
    async def get_sector(
        self,
        sector_type: str = "industry",
        **kwargs
    ) -> DataResult:
        """获取板块数据
        
        Args:
            sector_type: 板块类型
                - "industry": 行业涨幅榜
                - "concept": 概念涨幅榜
        """
        chain = self._chains.get(DataType.SECTOR)
        if not chain:
            return DataResult(success=False, error="No provider for SECTOR")
        
        return await chain.fetch(sector_type=sector_type, **kwargs)
    
    async def screen(self, query: str, perpage: int = 50, **kwargs) -> DataResult:
        """自然语言选股
        
        Args:
            query: 自然语言查询语句
                - "今日涨停股票"
                - "连续涨停天数大于2"
                - "市值小于50亿的科技股"
            perpage: 返回结果数量
        """
        chain = self._chains.get(DataType.SCREENING)
        if not chain:
            return DataResult(success=False, error="No provider for SCREENING")
        
        return await chain.fetch(query=query, perpage=perpage, **kwargs)
    
    async def get_index_constituents(
        self,
        index_code: str = "000300",
        **kwargs
    ) -> DataResult:
        """获取指数成分股
        
        Args:
            index_code: 指数代码 (000300=沪深300, 000905=中证500)
        """
        chain = self._chains.get(DataType.INDEX)
        if not chain:
            return DataResult(success=False, error="No provider for INDEX")
        
        return await chain.fetch(index_code=index_code, **kwargs)
    
    # ========== 监控统计 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "initialized": self._initialized,
            "providers": [p.name for p in self._providers],
            "chains": {},
        }
        
        for data_type, chain in self._chains.items():
            stats["chains"][data_type.value] = chain.get_stats_summary()
        
        if self._time_strategy:
            stats["trading_session"] = self._time_strategy.get_session_info()
        
        return stats
    
    def get_session_info(self) -> Dict:
        """获取当前交易时段信息"""
        if self._time_strategy:
            return self._time_strategy.get_session_info()
        return {}
    
    @property
    def is_trading_hours(self) -> bool:
        """是否在交易时段"""
        if self._time_strategy:
            return self._time_strategy.is_trading_hours()
        return False


# 全局单例
_manager_instance: Optional[DataServiceManager] = None


async def get_data_service() -> DataServiceManager:
    """获取数据服务单例
    
    Example:
        service = await get_data_service()
        result = await service.get_quotes(codes=["000001"])
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = DataServiceManager()
        await _manager_instance.initialize()
    return _manager_instance


async def close_data_service() -> None:
    """关闭数据服务单例"""
    global _manager_instance
    if _manager_instance:
        await _manager_instance.close()
        _manager_instance = None
