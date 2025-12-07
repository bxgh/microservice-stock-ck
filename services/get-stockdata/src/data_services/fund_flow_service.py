# -*- coding: utf-8 -*-
"""
EPIC-007 资金流向服务 (FundFlowService)

从分笔成交数据计算主力资金流向。

核心功能:
1. 资金流向统计: 大单/中单/小单买卖统计
2. 主力资金净流入

数据源: 从 TickService 派生计算

@author: EPIC-007 Story 007.09
@date: 2025-12-07
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import pandas as pd
import numpy as np

from .cache_manager import CacheManager
from .time_aware_strategy import get_time_strategy
from .tick_service import TickService

logger = logging.getLogger(__name__)


class FundFlowService:
    """资金流向服务
    
    从分笔成交数据计算主力资金流向。
    
    大单/中单/小单分类标准 (可配置):
    - 大单: 成交额 >= 100万
    - 中单: 10万 <= 成交额 < 100万
    - 小单: 成交额 < 10万
    
    Example:
        service = FundFlowService()
        await service.initialize()
        
        # 获取资金流向
        flow = await service.get_fund_flow('600519', '2025-12-06')
        print(f"大单净流入: {flow['large_net']}")
        
        await service.close()
    """
    
    # 大单/中单/小单阈值 (元)
    LARGE_THRESHOLD = 1000000   # 100万
    MEDIUM_THRESHOLD = 100000   # 10万
    
    def __init__(
        self,
        tick_service: Optional[TickService] = None,
        cache_manager: Optional[CacheManager] = None,
        enable_cache: bool = True,
    ):
        """初始化
        
        Args:
            tick_service: 分笔服务 (可注入)
            cache_manager: 缓存管理器
            enable_cache: 是否启用缓存
        """
        self._tick_service = tick_service
        self._cache_manager = cache_manager
        self._enable_cache = enable_cache
        
        self._initialized = False
        self._lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
        
        # 统计信息
        self._stats: Dict[str, Any] = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'tick_fetches': 0,
        }
    
    async def initialize(self) -> bool:
        """初始化服务"""
        async with self._lock:
            if self._initialized:
                return True
            
            logger.info("Initializing FundFlowService...")
            
            # 初始化 TickService
            if self._tick_service is None:
                self._tick_service = TickService(enable_cache=self._enable_cache)
            
            if not await self._tick_service.initialize():
                logger.error("TickService init failed")
                return False
            
            # 初始化缓存管理器
            if self._enable_cache:
                if self._cache_manager is None:
                    self._cache_manager = CacheManager()
                
                if not await self._cache_manager.initialize():
                    logger.warning("CacheManager init failed, caching disabled")
                    self._enable_cache = False
            
            self._initialized = True
            logger.info("✅ FundFlowService initialized")
            return True
    
    async def close(self) -> None:
        """关闭服务"""
        if self._tick_service:
            await self._tick_service.close()
        if self._cache_manager:
            await self._cache_manager.close()
        
        self._initialized = False
        logger.info("FundFlowService closed")
    
    async def _ensure_initialized(self) -> bool:
        """确保服务已初始化"""
        if not self._initialized:
            return await self.initialize()
        return True
    
    # ========== 资金流向 ==========
    
    async def get_fund_flow(
        self,
        code: str,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取资金流向
        
        Args:
            code: 股票代码
            date: 日期 (YYYY-MM-DD)，默认今天
            
        Returns:
            Dict: {
                'code': str,
                'date': str,
                'large_buy': float,    # 大单买入
                'large_sell': float,   # 大单卖出
                'large_net': float,    # 大单净流入
                'medium_buy': float,   # 中单买入
                'medium_sell': float,  # 中单卖出
                'medium_net': float,   # 中单净流入
                'small_buy': float,    # 小单买入
                'small_sell': float,   # 小单卖出
                'small_net': float,    # 小单净流入
                'total_net': float,    # 总净流入 (=大单+中单净流入)
            }
        """
        if not await self._ensure_initialized():
            raise RuntimeError("FundFlowService not initialized")
        
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        async with self._stats_lock:
            self._stats['total_requests'] += 1
        
        # 缓存键
        cache_key = f"fundflow:{code}:{date}"
        
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached
            
            async with self._stats_lock:
                self._stats['cache_misses'] += 1
        
        # 获取分笔数据
        async with self._stats_lock:
            self._stats['tick_fetches'] += 1
        
        tick_df = await self._tick_service.get_tick(code, date)
        
        if tick_df is None or tick_df.empty:
            return self._empty_result(code, date)
        
        # 计算资金流向
        result = self._calculate_fund_flow(tick_df, code, date)
        
        # 缓存 (时段感知 TTL)
        if self._enable_cache and result:
            strategy = get_time_strategy()
            ttl = strategy.get_cache_ttl('tick')  # 使用 tick 的 TTL
            await self._cache_manager.set(cache_key, result, ttl=ttl)
        
        return result
    
    def _calculate_fund_flow(
        self,
        df: pd.DataFrame,
        code: str,
        date: str
    ) -> Dict[str, Any]:
        """计算资金流向"""
        try:
            result = {
                'code': code,
                'date': date,
                'large_buy': 0.0,
                'large_sell': 0.0,
                'large_net': 0.0,
                'medium_buy': 0.0,
                'medium_sell': 0.0,
                'medium_net': 0.0,
                'small_buy': 0.0,
                'small_sell': 0.0,
                'small_net': 0.0,
                'total_net': 0.0,
            }
            
            # 确定成交额字段
            amount_col = None
            for col in ['amount', '成交额', 'turnover']:
                if col in df.columns:
                    amount_col = col
                    break
            
            if amount_col is None:
                logger.warning("No amount column found in tick data")
                return result
            
            # 确定买卖方向字段
            direction_col = None
            for col in ['direction', '买卖方向', 'type']:
                if col in df.columns:
                    direction_col = col
                    break
            
            # 遍历每笔交易
            for _, row in df.iterrows():
                amount = float(row.get(amount_col, 0))
                
                # 判断买卖方向
                is_buy = True  # 默认买入
                if direction_col:
                    direction = str(row.get(direction_col, '')).upper()
                    if direction in ['S', 'SELL', '卖', '卖出', '1']:
                        is_buy = False
                
                # 分类
                if amount >= self.LARGE_THRESHOLD:
                    if is_buy:
                        result['large_buy'] += amount
                    else:
                        result['large_sell'] += amount
                elif amount >= self.MEDIUM_THRESHOLD:
                    if is_buy:
                        result['medium_buy'] += amount
                    else:
                        result['medium_sell'] += amount
                else:
                    if is_buy:
                        result['small_buy'] += amount
                    else:
                        result['small_sell'] += amount
            
            # 计算净流入
            result['large_net'] = result['large_buy'] - result['large_sell']
            result['medium_net'] = result['medium_buy'] - result['medium_sell']
            result['small_net'] = result['small_buy'] - result['small_sell']
            result['total_net'] = result['large_net'] + result['medium_net']  # 主力资金 = 大单+中单
            
            return result
            
        except Exception as e:
            logger.error(f"Calculate fund flow failed: {e}")
            return self._empty_result(code, date)
    
    def _empty_result(self, code: str, date: str) -> Dict[str, Any]:
        """返回空结果"""
        return {
            'code': code,
            'date': date,
            'large_buy': 0.0,
            'large_sell': 0.0,
            'large_net': 0.0,
            'medium_buy': 0.0,
            'medium_sell': 0.0,
            'medium_net': 0.0,
            'small_buy': 0.0,
            'small_sell': 0.0,
            'small_net': 0.0,
            'total_net': 0.0,
        }
    
    # ========== 监控统计 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.copy()
        
        if stats['total_requests'] > 0:
            stats['cache_hit_rate'] = f"{stats['cache_hits'] / stats['total_requests'] * 100:.1f}%"
        else:
            stats['cache_hit_rate'] = "N/A"
        
        return stats
