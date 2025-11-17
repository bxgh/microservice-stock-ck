#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版股票数据服务
支持按数据类型配置数据源优先级
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class DataType(Enum):
    """数据类型枚举"""
    REALTIME = "realtime"      # 实时行情
    HISTORICAL = "historical"  # 历史K线
    TICK = "tick"              # 分笔成交
    FINANCIAL = "financial"    # 财务报表
    SECTOR = "sector"          # 板块指数
    MACRO = "macro"            # 宏观经济

class MarketType(Enum):
    """市场类型枚举"""
    A_STOCKS = "A股"
    HK_STOCKS = "港股"
    US_STOCKS = "美股"

class EnhancedStockDataService:
    """增强版股票数据服务，支持数据源优先级策略"""

    def __init__(self):
        # 数据源优先级配置
        self.data_source_priorities = self._init_data_source_priorities()

        # 数据源能力配置
        self.source_capabilities = self._init_source_capabilities()

        # 缓存配置
        self.cache = {}
        self.cache_ttl = {
            DataType.REALTIME: 5,      # 实时数据缓存5秒
            DataType.HISTORICAL: 3600,  # 历史数据缓存1小时
            DataType.TICK: 2,           # 分笔数据缓存2秒
            DataType.FINANCIAL: 86400, # 财务数据缓存1天
            DataType.SECTOR: 300,      # 板块数据缓存5分钟
            DataType.MACRO: 7200       # 宏观数据缓存2小时
        }

        # 数据源健康状态
        self.source_health = self._init_source_health()

    def _init_data_source_priorities(self) -> Dict:
        """初始化数据源优先级配置"""
        return {
            DataType.REALTIME: {
                MarketType.A_STOCKS: ["akshare", "tushare", "mootdx"],
                MarketType.HK_STOCKS: ["akshare", "mootdx", "tushare"],
                MarketType.US_STOCKS: ["yfinance", "alpha_vantage", "pandas"],
            },
            DataType.HISTORICAL: {
                MarketType.A_STOCKS: ["akshare", "baostock", "tushare"],
                MarketType.HK_STOCKS: ["akshare", "mootdx"],
                MarketType.US_STOCKS: ["yfinance", "pandas", "alpha_vantage"],
            },
            DataType.TICK: {
                MarketType.A_STOCKS: ["akshare", "mootdx"],
                MarketType.HK_STOCKS: ["akshare", "mootdx"],
                MarketType.US_STOCKS: ["yfinance", "alpha_vantage"],
            },
            DataType.FINANCIAL: {
                MarketType.A_STOCKS: ["akshare", "tushare", "baostock"],
                MarketType.US_STOCKS: ["yfinance", "alpha_vantage", "pandas"],
            },
            DataType.SECTOR: {
                MarketType.A_STOCKS: ["akshare", "tushare"],
                MarketType.US_STOCKS: ["yfinance", "pandas"],
            },
            DataType.MACRO: {
                "中国": ["akshare", "tushare"],
                "全球": ["pandas", "alpha_vantage"],
            }
        }

    def _init_source_capabilities(self) -> Dict:
        """初始化数据源能力配置"""
        return {
            "akshare": {
                "supported_markets": [MarketType.A_STOCKS, MarketType.HK_STOCKS, MarketType.US_STOCKS],
                "supported_data_types": [
                    DataType.REALTIME, DataType.HISTORICAL, DataType.TICK,
                    DataType.FINANCIAL, DataType.SECTOR, DataType.MACRO
                ],
                "rate_limit": "100次/分钟",
                "cost": "免费",
                "latency": "0.25-1.2s"
            },
            "yfinance": {
                "supported_markets": [MarketType.US_STOCKS, MarketType.HK_STOCKS, MarketType.A_STOCKS],
                "supported_data_types": [
                    DataType.REALTIME, DataType.HISTORICAL, DataType.FINANCIAL, DataType.SECTOR
                ],
                "rate_limit": "2000次/小时",
                "cost": "免费",
                "latency": "0.3-0.5s"
            },
            "tushare": {
                "supported_markets": [MarketType.A_STOCKS, MarketType.HK_STOCKS],
                "supported_data_types": [
                    DataType.REALTIME, DataType.HISTORICAL, DataType.FINANCIAL, DataType.SECTOR
                ],
                "rate_limit": "500次/天(免费)",
                "cost": "付费(积分)",
                "latency": "0.2-0.8s"
            },
            "alpha_vantage": {
                "supported_markets": [MarketType.US_STOCKS],
                "supported_data_types": [
                    DataType.REALTIME, DataType.HISTORICAL, DataType.TICK, DataType.FINANCIAL
                ],
                "rate_limit": "500次/天(免费)",
                "cost": "付费",
                "latency": "0.4-1.0s"
            },
            "baostock": {
                "supported_markets": [MarketType.A_STOCKS],
                "supported_data_types": [DataType.HISTORICAL, DataType.FINANCIAL],
                "rate_limit": "无限制",
                "cost": "免费",
                "latency": "0.5-1.5s"
            },
            "mootdx": {
                "supported_markets": [MarketType.A_STOCKS, MarketType.HK_STOCKS, MarketType.US_STOCKS],
                "supported_data_types": [DataType.REALTIME, DataType.TICK, DataType.HISTORICAL],
                "rate_limit": "1000次/分钟",
                "cost": "免费",
                "latency": "0.3-0.7s"
            }
        }

    def _init_source_health(self) -> Dict:
        """初始化数据源健康状态"""
        return {
            "akshare": {"status": "healthy", "last_check": datetime.now(), "failures": 0},
            "yfinance": {"status": "healthy", "last_check": datetime.now(), "failures": 0},
            "tushare": {"status": "healthy", "last_check": datetime.now(), "failures": 0},
            "alpha_vantage": {"status": "healthy", "last_check": datetime.now(), "failures": 0},
            "baostock": {"status": "healthy", "last_check": datetime.now(), "failures": 0},
            "mootdx": {"status": "healthy", "last_check": datetime.now(), "failures": 0}
        }

    def detect_market_type(self, symbol: str) -> MarketType:
        """检测股票代码所属市场类型"""
        if len(symbol) == 6 and symbol.isdigit():
            if symbol.startswith(('000', '002', '300')):
                return MarketType.A_STOCKS
            elif symbol.startswith('600'):
                return MarketType.A_STOCKS
            elif symbol.startswith('688'):
                return MarketType.A_STOCKS
        elif symbol.isdigit() and len(symbol) <= 5:
            return MarketType.US_STOCKS
        elif symbol.isalpha():
            return MarketType.US_STOCKS
        elif '.' in symbol:
            if symbol.endswith('.SZ') or symbol.endswith('.SH'):
                return MarketType.A_STOCKS
            elif symbol.endswith('.HK'):
                return MarketType.HK_STOCKS

        return MarketType.US_STOCKS  # 默认为美股

    def get_priority_sources(self, data_type: DataType, market_type: MarketType) -> List[str]:
        """获取指定数据类型和市场类型的数据源优先级列表"""
        priority_list = self.data_source_priorities.get(data_type, {}).get(market_type, [])

        # 过滤掉不健康的数据源
        healthy_sources = []
        for source in priority_list:
            if self.source_health[source]["status"] == "healthy":
                healthy_sources.append(source)
            elif self.source_health[source]["failures"] < 3:  # 失败次数少于3次，仍然尝试
                healthy_sources.append(source)

        return healthy_sources

    def update_source_health(self, source: str, success: bool):
        """更新数据源健康状态"""
        if source in self.source_health:
            if success:
                self.source_health[source]["status"] = "healthy"
                self.source_health[source]["failures"] = 0
                self.source_health[source]["last_check"] = datetime.now()
            else:
                self.source_health[source]["failures"] += 1
                self.source_health[source]["last_check"] = datetime.now()
                if self.source_health[source]["failures"] >= 3:
                    self.source_health[source]["status"] = "unhealthy"

    def _get_cache_key(self, method: str, *args) -> str:
        """生成缓存键"""
        return f"{method}:{':'.join(map(str, args))}"

    def _is_cache_valid(self, cache_key: str, data_type: DataType) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self.cache:
            return False

        cache_time = self.cache[cache_key].get('timestamp')
        if not cache_time:
            return False

        ttl = self.cache_ttl.get(data_type, 300)
        return (datetime.now() - cache_time).seconds < ttl

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if cache_key in self.cache:
            return self.cache[cache_key]['data']
        return None

    def _set_cache(self, cache_key: str, data: Any):
        """设置缓存"""
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }

    async def get_realtime_data(self, symbol: str) -> Dict[str, Any]:
        """获取实时行情数据 - 优先使用最快的实时数据源"""
        market_type = self.detect_market_type(symbol)
        cache_key = self._get_cache_key("realtime", symbol, market_type.value)

        # 检查缓存
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        # 获取优先级数据源
        priority_sources = self.get_priority_sources(DataType.REALTIME, market_type)

        for source in priority_sources:
            try:
                logger.info(f"尝试使用 {source} 获取 {symbol} 实时数据")
                data = await self._fetch_data_from_source(source, symbol, DataType.REALTIME)

                if data:
                    self.update_source_health(source, True)
                    self._set_cache(cache_key, data)
                    data['data_source'] = source
                    data['data_type'] = DataType.REALTIME.value
                    return data

            except Exception as e:
                logger.error(f"{source} 获取实时数据失败: {e}")
                self.update_source_health(source, False)
                continue

        # 所有数据源都失败，返回模拟数据
        return self._get_fallback_data(symbol, DataType.REALTIME)

    async def get_historical_data(self, symbol: str, period: str = "1mo", interval: str = "1d") -> Dict[str, Any]:
        """获取历史数据 - 优先使用数据完整的数据源"""
        market_type = self.detect_market_type(symbol)
        cache_key = self._get_cache_key("historical", symbol, period, interval)

        # 检查缓存
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        # 获取优先级数据源
        priority_sources = self.get_priority_sources(DataType.HISTORICAL, market_type)

        for source in priority_sources:
            try:
                logger.info(f"尝试使用 {source} 获取 {symbol} 历史数据")
                data = await self._fetch_data_from_source(source, symbol, DataType.HISTORICAL, period, interval)

                if data:
                    self.update_source_health(source, True)
                    self._set_cache(cache_key, data)
                    data['data_source'] = source
                    data['data_type'] = DataType.HISTORICAL.value
                    return data

            except Exception as e:
                logger.error(f"{source} 获取历史数据失败: {e}")
                self.update_source_health(source, False)
                continue

        return self._get_fallback_data(symbol, DataType.HISTORICAL, period, interval)

    async def get_tick_data(self, symbol: str) -> Dict[str, Any]:
        """获取分笔成交数据 - 优先使用高频数据源"""
        market_type = self.detect_market_type(symbol)
        cache_key = self._get_cache_key("tick", symbol)

        # 检查缓存
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        # 获取优先级数据源
        priority_sources = self.get_priority_sources(DataType.TICK, market_type)

        for source in priority_sources:
            try:
                logger.info(f"尝试使用 {source} 获取 {symbol} 分笔数据")
                data = await self._fetch_data_from_source(source, symbol, DataType.TICK)

                if data:
                    self.update_source_health(source, True)
                    self._set_cache(cache_key, data)
                    data['data_source'] = source
                    data['data_type'] = DataType.TICK.value
                    return data

            except Exception as e:
                logger.error(f"{source} 获取分笔数据失败: {e}")
                self.update_source_health(source, False)
                continue

        return self._get_fallback_data(symbol, DataType.TICK)

    async def get_financial_data(self, symbol: str) -> Dict[str, Any]:
        """获取财务数据 - 优先使用权威数据源"""
        market_type = self.detect_market_type(symbol)
        cache_key = self._get_cache_key("financial", symbol)

        # 检查缓存
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        # 获取优先级数据源
        priority_sources = self.get_priority_sources(DataType.FINANCIAL, market_type)

        for source in priority_sources:
            try:
                logger.info(f"尝试使用 {source} 获取 {symbol} 财务数据")
                data = await self._fetch_data_from_source(source, symbol, DataType.FINANCIAL)

                if data:
                    self.update_source_health(source, True)
                    self._set_cache(cache_key, data)
                    data['data_source'] = source
                    data['data_type'] = DataType.FINANCIAL.value
                    return data

            except Exception as e:
                logger.error(f"{source} 获取财务数据失败: {e}")
                self.update_source_health(source, False)
                continue

        return self._get_fallback_data(symbol, DataType.FINANCIAL)

    async def get_sector_data(self, sector_code: str) -> Dict[str, Any]:
        """获取板块数据"""
        cache_key = self._get_cache_key("sector", sector_code)

        # 检查缓存
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        # 获取优先级数据源
        priority_sources = self.get_priority_sources(DataType.SECTOR, MarketType.A_STOCKS)

        for source in priority_sources:
            try:
                logger.info(f"尝试使用 {source} 获取板块 {sector_code} 数据")
                data = await self._fetch_sector_data_from_source(source, sector_code)

                if data:
                    self.update_source_health(source, True)
                    self._set_cache(cache_key, data)
                    data['data_source'] = source
                    data['data_type'] = DataType.SECTOR.value
                    return data

            except Exception as e:
                logger.error(f"{source} 获取板块数据失败: {e}")
                self.update_source_health(source, False)
                continue

        return self._get_fallback_data(sector_code, DataType.SECTOR)

    async def _fetch_data_from_source(self, source: str, symbol: str, data_type: DataType, *args) -> Optional[Dict]:
        """从指定数据源获取数据"""
        # 这里会调用具体的数据源API
        # 实际实现需要根据各个数据源的具体API来编写
        logger.info(f"从 {source} 获取 {symbol} 的 {data_type.value} 数据")

        # 模拟数据获取
        await asyncio.sleep(0.1)  # 模拟网络延迟

        return {
            "symbol": symbol.upper(),
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "simulated": True
        }

    async def _fetch_sector_data_from_source(self, source: str, sector_code: str) -> Optional[Dict]:
        """从指定数据源获取板块数据"""
        logger.info(f"从 {source} 获取板块 {sector_code} 数据")
        await asyncio.sleep(0.1)

        return {
            "sector_code": sector_code,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "simulated": True
        }

    def _get_fallback_data(self, symbol: str, data_type: DataType, *args) -> Dict[str, Any]:
        """获取备用数据"""
        return {
            "symbol": symbol.upper(),
            "data_type": data_type.value,
            "timestamp": datetime.now().isoformat(),
            "source": "fallback",
            "error": "所有数据源不可用",
            "message": f"无法获取 {data_type.value} 数据"
        }

    def get_source_status(self) -> Dict[str, Any]:
        """获取所有数据源的健康状态"""
        return {
            "data_sources": self.source_health,
            "source_capabilities": self.source_capabilities,
            "priority_config": {
                data_type.value: {
                    market.value: sources
                    for market, sources in markets.items()
                }
                for data_type, markets in self.data_source_priorities.items()
            }
        }