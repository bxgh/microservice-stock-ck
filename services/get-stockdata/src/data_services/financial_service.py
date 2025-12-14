# -*- coding: utf-8 -*-
"""
EPIC-007 财务报表服务 (FinancialService)

提供个股财务指标和财务报表摘要查询。

核心功能:
1. 财务摘要: 利润表/资产负债表/现金流量表关键指标
2. 财务指标: PE/PB/ROE/EPS等分析指标
3. PE/PB快速查询

数据源: akshare

@author: EPIC-007 Story 007.08
@date: 2025-12-07
"""

import asyncio
import logging
import math
from typing import Any, Dict, List, Optional
from datetime import datetime

import pandas as pd

from .cache_manager import CacheManager
from .time_aware_strategy import get_time_strategy
from .akshare_client import akshare_client

logger = logging.getLogger(__name__)

# Unit conversion constants
YUAN_TO_YI_YUAN = 100_000_000  # 元 -> 亿元 (Yuan to 100 Million Yuan)
FINANCIAL_PRECISION = 4  # 财务数据精度（小数位）


# 财务报表字段映射 (Sina -> Standard)
SINA_FIELD_MAPPING = {
    # Income Statement
    '营业总收入': 'revenue',
    '营业收入': 'revenue', # Fallback
    '营业成本': 'operating_cost',
    '营业利润': 'operating_profit',
    '净利润': 'net_profit',
    
    # Balance Sheet
    '资产总计': 'total_assets',
    '股东权益合计': 'net_assets',
    '所有者权益(或股东权益)合计': 'net_assets', # Synonym
    '商誉': 'goodwill',
    '货币资金': 'monetary_funds',
    '应收账款': 'accounts_receivable',
    '存货': 'inventory',
    '应付账款': 'accounts_payable',
    
    # Debt (Calculated fields usually, but mapping simple ones)
    '短期借款': 'short_term_debt',
    '长期借款': 'long_term_debt',
    '应付债券': 'bond_payable',
    
    # Cash Flow
    '经营活动产生的现金流量净额': 'operating_cash_flow',
}



class FinancialService:
    """财务报表服务
    
    提供个股财务指标和财务报表摘要查询。
    
    Example:
        service = FinancialService()
        await service.initialize()
        
        # 财务摘要
        summary = await service.get_financial_summary('600519')
        
        # 财务指标
        indicators = await service.get_financial_indicators('600519')
        
        # PE/PB
        pe_pb = await service.get_pe_pb('600519')
        
        await service.close()
    """
    
    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        enable_cache: bool = True,
        timeout: int = 30,
    ):
        """初始化
        
        Args:
            cache_manager: 缓存管理器
            enable_cache: 是否启用缓存
            timeout: API 超时时间(秒)
        """
        self._cache_manager = cache_manager
        self._enable_cache = enable_cache
        self._timeout = timeout
        
        self._initialized = False
        self._lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
        
        # 统计信息
        self._stats: Dict[str, Any] = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'akshare_calls': 0,
            'timeout_errors': 0,
        }
    
    async def initialize(self) -> bool:
        """初始化服务"""
        async with self._lock:
            if self._initialized:
                return True
            
            logger.info("Initializing FinancialService...")
            
            # 初始化缓存管理器
            if self._enable_cache:
                if self._cache_manager is None:
                    self._cache_manager = CacheManager()
                
                if not await self._cache_manager.initialize():
                    logger.warning("CacheManager init failed, caching disabled")
                    self._enable_cache = False
            
            self._initialized = True
            logger.info("✅ FinancialService initialized")
            return True
    
    async def close(self) -> None:
        """关闭服务"""
        if self._cache_manager:
            await self._cache_manager.close()
        
        self._initialized = False
        logger.info("FinancialService closed")
    
    async def _ensure_initialized(self) -> bool:
        """确保服务已初始化"""
        if not self._initialized:
            return await self.initialize()
        return True
    
    async def _call_akshare(self, func_name: str, **kwargs) -> Optional[pd.DataFrame]:
        """调用 akshare API (委托给 AkShareClient)"""
        try:
            async with self._stats_lock:
                self._stats['akshare_calls'] += 1
                
            return await akshare_client.call(func_name, **kwargs)
            
        except asyncio.TimeoutError:
            logger.error(f"FinancialService call {func_name} timeout")
            async with self._stats_lock:
                self._stats['timeout_errors'] += 1
            return None
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"FinancialService call {func_name} data error: {e}")
            async with self._stats_lock:
                self._stats.setdefault('data_errors', 0)
                self._stats['data_errors'] += 1
            return None
        except Exception as e:
            logger.error(f"FinancialService call {func_name} unexpected error: {e}", exc_info=True)
            async with self._stats_lock:
                self._stats.setdefault('general_errors', 0)
                self._stats['general_errors'] += 1
            return None
    
    # ========== 财务摘要 ==========
    
    async def get_financial_summary(
        self,
        code: str,
    ) -> Dict[str, Any]:
        """获取财务摘要
        
        Args:
            code: 股票代码 (如 '600519')
            
        Returns:
            Dict: 财务摘要信息
        """
        if not await self._ensure_initialized():
            raise RuntimeError("FinancialService not initialized")
        
        async with self._stats_lock:
            self._stats['total_requests'] += 1
        
        # 缓存键
        cache_key = f"financial:summary:{code}"
        
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached
            
            async with self._stats_lock:
                self._stats['cache_misses'] += 1
        
        # 调用 akshare
        df = await self._call_akshare('stock_financial_abstract', symbol=code)
        
        if df is None or df.empty:
            return {}
        
        # 转换为字典格式
        result = self._parse_financial_summary(df)
        
        # 缓存 (1天，财务数据更新频率低)
        if self._enable_cache and result:
            await self._cache_manager.set(cache_key, result, ttl=86400)
        
        return result
    
    def _parse_financial_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """解析财务摘要数据"""
        try:
            result = {
                'code': '',
                'report_date': '',
                'data': {},
            }
            
            # 获取最近的报告期
            date_cols = [col for col in df.columns if col not in ['选项', '指标']]
            if date_cols:
                latest_date = date_cols[0]
                result['report_date'] = latest_date
                
                # 提取关键指标
                for _, row in df.iterrows():
                    indicator = row.get('指标', row.get('选项', ''))
                    value = row.get(latest_date, None)
                    if indicator and pd.notna(value):
                        result['data'][indicator] = value
            
            return result
            
        except Exception as e:
            logger.error(f"Parse financial summary failed: {e}")
            return {}
    
    # ========== 财务指标 ==========
    
    async def get_financial_indicators(
        self,
        code: str,
        start_year: str = '2020',
    ) -> pd.DataFrame:
        """获取财务分析指标
        
        Args:
            code: 股票代码
            start_year: 起始年份
            
        Returns:
            DataFrame: 财务指标数据
        """
        if not await self._ensure_initialized():
            raise RuntimeError("FinancialService not initialized")
        
        async with self._stats_lock:
            self._stats['total_requests'] += 1
        
        # 缓存键
        cache_key = f"financial:indicators:{code}:{start_year}"
        
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached
            
            async with self._stats_lock:
                self._stats['cache_misses'] += 1
        
        # 调用 akshare
        df = await self._call_akshare(
            'stock_financial_analysis_indicator',
            symbol=code,
            start_year=start_year
        )
        
        if df is None:
            return pd.DataFrame()
        
        # 缓存 (1天)
        if self._enable_cache and not df.empty:
            await self._cache_manager.set(cache_key, df, ttl=86400)
        
        return df
    
    # ========== PE/PB 快速查询 ==========
    
    async def get_pe_pb(
        self,
        code: str,
    ) -> Dict[str, Any]:
        """获取 PE/PB 估值指标
        
        Args:
            code: 股票代码
            
        Returns:
            Dict: {'pe': float, 'pb': float, 'pe_ttm': float}
        """
        if not await self._ensure_initialized():
            raise RuntimeError("FinancialService not initialized")
        
        async with self._stats_lock:
            self._stats['total_requests'] += 1
        
        # 缓存键
        cache_key = f"financial:pe_pb:{code}"
        
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached
            
            async with self._stats_lock:
                self._stats['cache_misses'] += 1
        
        result = {
            'pe': None,
            'pb': None,
            'pe_ttm': None,
            'code': code,
        }
        
        # 从财务摘要中提取
        summary = await self.get_financial_summary(code)
        
        if summary and 'data' in summary:
            data = summary['data']
            # 尝试提取 PE/PB 相关指标
            for key, value in data.items():
                key_lower = key.lower()
                if 'pe' in key_lower or '市盈率' in key:
                    try:
                        result['pe'] = float(value)
                    except (ValueError, TypeError):
                        pass
                elif 'pb' in key_lower or '市净率' in key:
                    try:
                        result['pb'] = float(value)
                    except (ValueError, TypeError):
                        pass
        
        # 缓存 (时段感知 TTL)
        if self._enable_cache:
            strategy = get_time_strategy()
            ttl = strategy.get_cache_ttl('ranking')  # 使用 ranking 的 TTL
            await self._cache_manager.set(cache_key, result, ttl=ttl)
        
        return result
    
    # ========== EPIC-002: 增强财务数据 ==========

    async def get_enhanced_indicators(self, code: str) -> Dict[str, Any]:
        """获取增强财务指标 (EPIC-002)
        
        Args:
            code: 股票代码
            
        Returns:
            Dict: 包含完整财务报表字段的字典
        """
        # 复用 get_financial_history 获取最新一期数据
        history = await self.get_financial_history(code, periods=1)
        if not history or not history.get('data'):
            return {}
            
        return history['data'][0]

    async def get_financial_history(
        self, 
        code: str, 
        periods: int = 8, 
        report_type: str = 'Q'
    ) -> Dict[str, Any]:
        """获取历史财务数据
        
        Args:
            code: 股票代码
            periods: 期数
            report_type: 报告类型 (Q=季报, A=年报) - 目前 Sina 接口返回所有报告期
            
        Returns:
            Dict: {
                'stock_code': str,
                'periods': int,
                'data': List[Dict]
            }
        """
        if not await self._ensure_initialized():
             raise RuntimeError("FinancialService not initialized")

        cache_key = f"financial:history:{code}:{periods}"
        
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached:
                return cached
        
        # 并行获取三张表
        tasks = [
            self._fetch_sina_report(code, "资产负债表"),
            self._fetch_sina_report(code, "利润表"),
            self._fetch_sina_report(code, "现金流量表")
        ]
        
        balance_df, income_df, cash_df = await asyncio.gather(*tasks)
        
        # 合并数据
        # 假设所有DF都包含 '报告日' 列，且格式一致
        combined_data = {}
        
        for df in [balance_df, income_df, cash_df]:
            if df is not None and not df.empty and '报告日' in df.columns:
                records = df.to_dict('records')
                for row in records:
                    date = row['报告日']
                    if date not in combined_data:
                        combined_data[date] = {}
                    combined_data[date].update(row)
        
        # 转换为列表并排序
        sorted_dates = sorted(combined_data.keys(), reverse=True)
        result_list = []
        
        for date in sorted_dates[:periods]:
            data = combined_data[date]
            mapped_data = self._map_sina_fields(data)
            mapped_data['stock_code'] = code
            mapped_data['report_date'] = date
            
            # Calculate report_type from date (YYYYMMDD)
            _date_str = str(date)
            if _date_str.endswith('0331'):
                mapped_data['report_type'] = 'Q1'
            elif _date_str.endswith('0630'):
                mapped_data['report_type'] = 'Q2'
            elif _date_str.endswith('0930'):
                mapped_data['report_type'] = 'Q3'
            elif _date_str.endswith('1231'):
                mapped_data['report_type'] = 'Annual'
            else:
                mapped_data['report_type'] = 'Others'
            
            # 计算有息负债 (简略版: 短期借款 + 长期借款 + 应付债券)
            st_debt = float(data.get('短期借款', 0) or 0)
            lt_debt = float(data.get('长期借款', 0) or 0)
            bond = float(data.get('应付债券', 0) or 0)
            mapped_data['interest_bearing_debt'] = st_debt + lt_debt + bond
            
            # 转换单位 (元 -> 亿元)
            # Sina 数据通常单位是 元
            for field in ['revenue', 'operating_cost', 'operating_profit', 'net_profit',
                          'total_assets', 'net_assets', 'goodwill', 'monetary_funds',
                          'interest_bearing_debt', 'accounts_receivable', 'inventory',
                          'accounts_payable', 'operating_cash_flow']:
                if field in mapped_data and mapped_data[field] is not None:
                    try:
                        val = float(mapped_data[field])
                        # Handle NaN with explicit check
                        if math.isnan(val):
                            mapped_data[field] = None
                        else:
                            mapped_data[field] = round(val / YUAN_TO_YI_YUAN, FINANCIAL_PRECISION)
                    except (ValueError, TypeError):
                        mapped_data[field] = None

            result_list.append(mapped_data)
            
        result = {
            'stock_code': code,
            'periods': len(result_list),
            'report_type': report_type,
            'data': result_list
        }
        
        if self._enable_cache and result_list:
            await self._cache_manager.set(cache_key, result, ttl=86400 * 7)
            
        return result

    async def _fetch_sina_report(self, code: str, symbol: str) -> Optional[pd.DataFrame]:
        """获取新浪财务报表"""
        return await self._call_akshare(
            'stock_financial_report_sina',
            stock=code,
            symbol=symbol
        )

    def _map_sina_fields(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """映射字段名"""
        result = {}
        for cn_key, en_key in SINA_FIELD_MAPPING.items():
            if cn_key in row:
                result[en_key] = row[cn_key]
        return result

    # ========== 监控统计 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.copy()
        
        if stats['total_requests'] > 0:
            stats['cache_hit_rate'] = f"{stats['cache_hits'] / stats['total_requests'] * 100:.1f}%"
        else:
            stats['cache_hit_rate'] = "N/A"
        
        return stats

