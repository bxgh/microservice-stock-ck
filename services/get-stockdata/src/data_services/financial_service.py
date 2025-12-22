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
from .akshare_client import akshare_client
from .time_aware_strategy import get_time_strategy
from storage.clickhouse_writer import ClickHouseWriter, FinancialIndicatorData

try:
    from api.routers.metrics import record_data_source_request
except ImportError:
    def record_data_source_request(source, success, duration):
        pass

import time
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
        clickhouse_writer: Optional[ClickHouseWriter] = None,
    ):
        """初始化
        
        Args:
            cache_manager: 缓存管理器
            enable_cache: 是否启用缓存
            timeout: API 超时时间(秒)
        """
        import os
        import aiohttp
        
        self._cache_manager = cache_manager
        self._enable_cache = enable_cache
        self._timeout = timeout
        
        # 云端 AkShare API 配置 (EPIC-002)
        self._akshare_api_url = os.getenv("AKSHARE_API_URL", "http://124.221.80.250:8003")
        self._proxy_url = os.getenv("PROXY_URL", "http://192.168.151.18:3128")
        self._session: Optional[aiohttp.ClientSession] = None
        self._clickhouse_writer = clickhouse_writer
        
        self._initialized = False
        self._lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()
        
        # 统计信息
        self._stats: Dict[str, Any] = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'akshare_calls': 0,
            'cloud_api_calls': 0,  # 新增：云端 API 调用次数
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
            
            # 初始化 HTTP session (EPIC-002)
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                trust_env=True # Allow reading proxy from env
            )
            logger.info(f"Cloud API endpoint: {self._akshare_api_url}")
            
            self._initialized = True
            logger.info("✅ FinancialService initialized")
            return True
    
    async def close(self) -> None:
        """关闭服务"""
        if self._cache_manager:
            await self._cache_manager.close()
        
        # 关闭 HTTP session
        if self._session:
            await self._session.close()
            self._session = None
        
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
    
    # ========== EPIC-002: 云端 API 调用 ==========
    
    async def _call_cloud_api(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """调用云端 AkShare API
        
        Args:
            endpoint: API 端点 (如 '/api/v1/finance/indicators/600519')
            
        Returns:
            Dict: API 返回的数据，失败返回 None
        """
        if not self._session:
            logger.error("HTTP session not initialized")
            return None
        
        url = f"{self._akshare_api_url}{endpoint}"
        start_time = time.time()
        success = False
        
        try:
            async with self._stats_lock:
                self._stats['cloud_api_calls'] += 1
            
            logger.debug(f"Calling cloud API: {url}")
            
            async with self._session.get(url, proxy=self._proxy_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.debug(f"Cloud API success: {endpoint}")
                    success = True
                    return data
                else:
                    error_text = await resp.text()
                    logger.warning(f"Cloud API returned {resp.status}: {error_text[:200]}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"Cloud API timeout: {endpoint}")
            async with self._stats_lock:
                self._stats['timeout_errors'] += 1
            return None
        except Exception as e:
            logger.error(f"Cloud API error: {e}", exc_info=True)
            return None
        finally:
            duration = time.time() - start_time
            record_data_source_request(f"cloud_akshare_finance", success, duration)
    
    # ========== EPIC-002: 增强财务数据 ==========

    async def get_enhanced_indicators(self, code: str) -> Dict[str, Any]:
        """获取增强财务指标 (EPIC-002)
        
        使用云端 AkShare API 获取完整的财务报表数据
        
        Args:
            code: 股票代码
            
        Returns:
            Dict: 包含完整财务报表字段的字典
        """
        if not await self._ensure_initialized():
            raise RuntimeError("FinancialService not initialized")
        
        async with self._stats_lock:
            self._stats['total_requests'] += 1
        
        # 缓存键
        cache_key = f"financial:enhanced:{code}"
        
        if self._enable_cache:
            cached = await self._cache_manager.get(cache_key)
            if cached is not None:
                async with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached
            
            async with self._stats_lock:
                self._stats['cache_misses'] += 1
        
        # 调用云端 API
        endpoint = f"/api/v1/finance/indicators/{code}"
        data = await self._call_cloud_api(endpoint)
        
        if not data:
            logger.warning(f"No financial data from cloud API for {code}")
            # 降级到旧方法
            return await self._get_enhanced_indicators_fallback(code)
        
        # 数据转换：元 -> 亿元
        result = self._transform_cloud_financial_data(data, code)
        
        # 写入 ClickHouse (Story 9.2)
        if self._clickhouse_writer and result:
            try:
                # 获取解析后的日期对象，使用后立即从字典中移除，避免序列化问题
                report_date = result.pop('parsed_report_date', None) or datetime.now()
                
                fi_data = FinancialIndicatorData(
                    stock_code=code,
                    report_date=report_date,
                    report_type=result.get('report_type', 'Annual'),
                    revenue=self._safe_div(data.get('revenue'), YUAN_TO_YI_YUAN),
                    operating_cost=self._safe_div(data.get('operating_cost'), YUAN_TO_YI_YUAN),
                    operating_profit=self._safe_div(data.get('operating_profit'), YUAN_TO_YI_YUAN),
                    net_profit=self._safe_div(data.get('net_profit'), YUAN_TO_YI_YUAN),
                    total_assets=self._safe_div(data.get('total_assets'), YUAN_TO_YI_YUAN),
                    net_assets=self._safe_div(data.get('net_assets'), YUAN_TO_YI_YUAN),
                    goodwill=self._safe_div(data.get('goodwill'), YUAN_TO_YI_YUAN),
                    monetary_funds=self._safe_div(data.get('monetary_funds'), YUAN_TO_YI_YUAN),
                    interest_bearing_debt=self._safe_div(data.get('interest_bearing_debt'), YUAN_TO_YI_YUAN),
                    accounts_receivable=self._safe_div(data.get('accounts_receivable'), YUAN_TO_YI_YUAN),
                    inventory=self._safe_div(data.get('inventory'), YUAN_TO_YI_YUAN),
                    accounts_payable=self._safe_div(data.get('accounts_payable'), YUAN_TO_YI_YUAN),
                    operating_cash_flow=self._safe_div(data.get('operating_cash_flow'), YUAN_TO_YI_YUAN),
                    major_shareholder_pledge_ratio=0.0
                )
                await self._clickhouse_writer.write_financial_indicators([fi_data])
            except Exception as e:
                logger.error(f"Failed to write financial indicators to ClickHouse: {e}")

        # 缓存 (1天)
        if self._enable_cache and result:
            await self._cache_manager.set(cache_key, result, ttl=86400)
        
        return result

    def _safe_div(self, val: Any, divisor: float) -> float:
        """安全除法"""
        try:
            if val is None:
                return 0.0
            if isinstance(val, str) and not val.strip():
                return 0.0
            return float(val) / divisor
        except (ValueError, TypeError):
            return 0.0


    def _parse_report_date(self, date_str: str) -> Optional[datetime]:
        """解析非标准日期字符串"""
        if not date_str:
            return None
        
        try:
            # 1. 尝试标准格式
            return datetime.strptime(str(date_str), '%Y%m%d')
        except ValueError:
            pass
            
        try:
            # 2. 处理中文格式 "2024三季报"
            import re
            match = re.search(r'(\d{4})(.*)', str(date_str))
            if match:
                year = int(match.group(1))
                suffix = match.group(2)
                
                if '一季' in suffix or 'Q1' in suffix:
                    return datetime(year, 3, 31)
                elif '二季' in suffix or 'Q2' in suffix or '中报' in suffix:
                    return datetime(year, 6, 30)
                elif '三季' in suffix or 'Q3' in suffix:
                    return datetime(year, 9, 30)
                elif '年报' in suffix or 'Annual' in suffix or '四季' in suffix:
                    return datetime(year, 12, 31)
                    
            return None
        except Exception:
            return None

    def _transform_cloud_financial_data(self, data: Dict[str, Any], code: str) -> Dict[str, Any]:
        """转换云端 API 返回的财务数据
        
        将单位从元转换为亿元，并映射到标准的 Schema 字段
        """
        # 解析日期
        report_date_str = str(data.get('report_date', ''))
        parsed_date = self._parse_report_date(report_date_str)
        
        result = {
            'stock_code': code,
            'report_date': parsed_date.strftime('%Y%m%d') if parsed_date else datetime.now().strftime('%Y%m%d'),
            'parsed_report_date': parsed_date # 供内部使用
        }
        
        # 1. 计算 report_type (从 report_date 推断)
        if '一季' in report_date_str or 'Q1' in report_date_str:
            result['report_type'] = 'Q1'
        elif '二季' in report_date_str or '中报' in report_date_str or 'Q2' in report_date_str:
            result['report_type'] = 'Q2'
        elif '三季' in report_date_str or 'Q3' in report_date_str:
            result['report_type'] = 'Q3'
        elif '年报' in report_date_str or 'Annual' in report_date_str or '四季' in report_date_str:
            result['report_type'] = 'Annual'
        else:
             # 如果是标准日期，尝试推断
            if parsed_date:
                m = parsed_date.month
                if m == 3: result['report_type'] = 'Q1'
                elif m == 6: result['report_type'] = 'Q2'
                elif m == 9: result['report_type'] = 'Q3'
                elif m == 12: result['report_type'] = 'Annual'
                else: result['report_type'] = 'Q3'
            else:
                result['report_type'] = 'Q3'
        
        # 2. 需要转换单位的字段 (元 -> 亿元) 并映射 field names
        # Mapping: {cloud_field: schema_field}
        field_mapping = {
            'total_assets': 'total_assets',
            'total_equity': 'net_assets',       # Total Equity -> Net Assets
            'operating_income': 'revenue',      # Operating Income -> Revenue
            'operating_cost': 'operating_cost',
            'operating_profit': 'operating_profit',
            'net_profit': 'net_profit',
            'monetary_funds': 'monetary_funds',
            'inventory': 'inventory',
            'accounts_receivable': 'accounts_receivable',
            'net_operating_cash_flow': 'operating_cash_flow', # Map to operating_cash_flow
            'goodwill': 'goodwill'
        }
        
        for cloud_field, schema_field in field_mapping.items():
            result[schema_field] = self._safe_div(data.get(cloud_field), YUAN_TO_YI_YUAN)
        
        # 3. 计算有息负债 (利息负担债务)
        st_debt = float(data.get('short_term_loans') or 0)
        lt_debt = float(data.get('long_term_loans') or 0)
        bond = float(data.get('bond_payable') or 0)
        result['interest_bearing_debt'] = self._safe_div(st_debt + lt_debt + bond, YUAN_TO_YI_YUAN)
            
        # 4. 其他字段
        result['accounts_payable'] = 0.0
        result['major_shareholder_pledge_ratio'] = 0.0
        
        return result
    
    async def _get_enhanced_indicators_fallback(self, code: str) -> Dict[str, Any]:
        """降级方法：使用旧的新浪财经 API"""
        logger.info(f"Using fallback method for {code}")
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

