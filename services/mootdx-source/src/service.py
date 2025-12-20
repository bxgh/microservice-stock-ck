"""
MooTDX Service - 统一数据源服务 (重构版本)
整合本地数据源（mootdx, easyquotation）和云端 API 调用

重构改进:
- 路由表策略模式
- 异步执行同步调用
- 降级策略 (cloud -> local)
- 配置化魔法值
- 完整类型提示
- 数据源能力注册表
"""
import json
import logging
import time
import asyncio
import os
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

import grpc
import pandas as pd

from datasource.v1 import data_source_pb2, data_source_pb2_grpc
from ds_registry import DataSource  # 从本地 ds_registry 包导入
from ds_registry.handlers import EasyquotationHandler
from mootdx_client import MootdxAPIClient  # 使用 HTTP 客户端
from cloud_client import CloudAPIClient
from config import HistoryDefaults, QueryDefaults, DragonTigerDefaults, RetryConfig

logger = logging.getLogger("unified-datasource")


@dataclass
class RouteConfig:
    """路由配置"""
    handler: str  # 方法名
    source_name: str  # 数据源名称
    fallback_handler: Optional[str] = None  # 降级处理器
    fallback_source_name: Optional[str] = None  # 降级数据源名称


@dataclass
class SourceStats:
    """数据源调用统计"""
    success_count: int = 0
    failure_count: int = 0
    total_latency_ms: int = 0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
    
    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.success_count if self.success_count > 0 else 0.0


# 数据验证规则
VALIDATION_RULES = {
    "QUOTES": {
        "required_columns": ["code"],
        "min_rows": 1
    },
    "TICK": {
        "required_columns": ["time"],
        "min_rows": 1
    },
    "HISTORY": {
        "required_columns": ["date", "close"],
        "min_rows": 1
    },
    "FINANCE": {
        "required_columns": ["code"],
        "min_rows": 1
    },
    "VALUATION": {
        "required_columns": ["code"],
        "min_rows": 1
    },
}


class MooTDXService(data_source_pb2_grpc.DataSourceServiceServicer):
    """统一数据源服务 - 路由请求到本地或云端"""
    
    # 路由映射表
    ROUTING_TABLE = {
        data_source_pb2.DATA_TYPE_QUOTES: RouteConfig(
            handler="_fetch_quotes_mootdx",
            source_name=DataSource.MOOTDX,
            fallback_handler="_fetch_quotes_easyquotation",
            fallback_source_name=DataSource.EASYQUOTATION
        ),
        data_source_pb2.DATA_TYPE_TICK: RouteConfig(
            handler="_fetch_tick_mootdx",
            source_name=DataSource.MOOTDX
        ),
        data_source_pb2.DATA_TYPE_HISTORY: RouteConfig(
            handler="_fetch_history_baostock",
            source_name=DataSource.BAOSTOCK_API,
            fallback_handler="_fetch_history_mootdx"  # 降级到本地
        ),
        data_source_pb2.DATA_TYPE_RANKING: RouteConfig(
            handler="_fetch_ranking_akshare",
            source_name=DataSource.AKSHARE_API
        ),
        data_source_pb2.DATA_TYPE_SECTOR: RouteConfig(
            handler="_fetch_sector_pywencai",
            source_name=DataSource.PYWENCAI_API
        ),
        data_source_pb2.DATA_TYPE_FINANCE: RouteConfig(
            handler="_fetch_finance_akshare",
            source_name=DataSource.AKSHARE_API,
            fallback_handler="_fetch_finance_baostock",
            fallback_source_name=DataSource.BAOSTOCK_API
        ),
        data_source_pb2.DATA_TYPE_VALUATION: RouteConfig(
            handler="_fetch_valuation_akshare",
            source_name=DataSource.AKSHARE_API
        ),
        data_source_pb2.DATA_TYPE_INDEX: RouteConfig(
            handler="_fetch_index_baostock",
            source_name=DataSource.BAOSTOCK_API
        ),
        data_source_pb2.DATA_TYPE_INDUSTRY: RouteConfig(
            handler="_fetch_industry_baostock",
            source_name=DataSource.BAOSTOCK_API,
            fallback_handler="_fetch_industry_akshare",
            fallback_source_name=DataSource.AKSHARE_API
        ),
        # 龙虎榜数据 (使用 META 类型)
        data_source_pb2.DATA_TYPE_META: RouteConfig(
            handler="_fetch_dragon_tiger_akshare",
            source_name=DataSource.AKSHARE_API
        ),
    }
    
    def __init__(self):
        # 本地/HTTP 数据源客户端
        self.mootdx_client: Optional[MootdxAPIClient] = None
        self.easy_handler: Optional[EasyquotationHandler] = None
        
        # 云端 API 客户端
        self.cloud_client: Optional[CloudAPIClient] = None
        
        # 可观测性: 数据源统计
        self._stats: Dict[str, SourceStats] = {}
        self._stats_lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """初始化所有数据源"""
        try:
            # 1. 初始化 mootdx API 客户端
            self.mootdx_client = MootdxAPIClient()
            await self.mootdx_client.initialize()
            
            # 2. 初始化 easyquotation handler
            self.easy_handler = EasyquotationHandler()
            await self.easy_handler.initialize()
            
            # 3. 初始化云端 API 客户端
            self.cloud_client = CloudAPIClient()
            await self.cloud_client.initialize()
            logger.info("✓ Cloud API client initialized")
            
            logger.info("=== Unified DataSource Service Ready ===")
        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            raise
    
    async def close(self) -> None:
        """清理所有资源"""
        try:
            if self.mootdx_client:
                await self.mootdx_client.close()
            if self.easy_handler:
                await self.easy_handler.close()
            if self.cloud_client:
                await self.cloud_client.close()
            logger.info("All resources cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def FetchData(
        self, 
        request: data_source_pb2.DataRequest, 
        context: grpc.aio.ServicerContext
    ) -> data_source_pb2.DataResponse:
        """gRPC: 获取数据 - 根据 DataType 路由到不同数据源"""
        start_time = time.time()
        req_type = data_source_pb2.DataType.Name(request.type)
        logger.info(f"Request: type={req_type}, codes={list(request.codes)[:3]}")
        
        try:
            # 查找路由配置
            route = self.ROUTING_TABLE.get(request.type)
            if not route:
                return self._error_response(
                    f"Unsupported DataType: {req_type}",
                    DataSource.ERROR
                )
            
            # 执行主处理器
            handler_start = time.time()
            df, source_name = await self._execute_handler(
                route.handler,
                route.source_name,
                request.codes,
                dict(request.params)
            )
            handler_latency = int((time.time() - handler_start) * 1000)
            
            # 数据验证
            is_valid, validation_error = self._validate_data(df, request.type)
            
            # 如果主处理器失败或数据无效且有降级处理器，尝试降级
            if (df.empty or not is_valid) and route.fallback_handler:
                if validation_error:
                    logger.warning(f"{source_name} validation failed: {validation_error}, trying fallback")
                else:
                    logger.warning(f"{source_name} returned empty, trying fallback")
                
                # 记录主处理器失败统计
                await self._record_stats(source_name, success=False, latency_ms=handler_latency)
                
                # 尝试降级处理器
                fallback_start = time.time()
                fallback_source = route.fallback_source_name or "fallback"
                df, source_name = await self._execute_handler(
                    route.fallback_handler,
                    fallback_source,
                    request.codes,
                    dict(request.params)
                )
                handler_latency = int((time.time() - fallback_start) * 1000)
                
                # 验证降级数据
                is_valid, validation_error = self._validate_data(df, request.type)
            
            # 计算总延迟
            latency = int((time.time() - start_time) * 1000)
            
            # 记录统计
            success = not df.empty and is_valid
            await self._record_stats(source_name, success=success, latency_ms=handler_latency)
            
            # 返回响应
            return self._success_response(df, source_name, latency)
        
        except Exception as e:
            logger.error(f"Error fetching data: {e}", exc_info=True)
            latency = int((time.time() - start_time) * 1000)
            return data_source_pb2.DataResponse(
                success=False,
                error_message=str(e),
                source_name=DataSource.ERROR,
                latency_ms=latency
            )
    
    async def _execute_handler(
        self,
        handler_name: str,
        source_name: str,
        codes: List[str],
        params: Dict[str, Any]
    ) -> tuple[pd.DataFrame, str]:
        """
        执行数据处理器
        
        Returns:
            (DataFrame, source_name)
        """
        try:
            handler = getattr(self, handler_name)
            df = await handler(codes, params)
            return df, source_name
        except Exception as e:
            logger.warning(f"Handler {handler_name} failed: {e}")
            return pd.DataFrame(), source_name
    
    def _success_response(
        self,
        df: pd.DataFrame,
        source_name: str,
        latency: int
    ) -> data_source_pb2.DataResponse:
        """构建成功响应"""
        if df.empty:
            logger.warning(f"Empty result from {source_name}")
            return data_source_pb2.DataResponse(
                success=True,
                json_data="[]",
                source_name=source_name,
                latency_ms=latency,
                format="JSON"
            )
        
        json_str = df.to_json(orient="records", date_format="iso")
        logger.info(f"✓ {source_name} returned {len(df)} records in {latency}ms")
        
        return data_source_pb2.DataResponse(
            success=True,
            json_data=json_str,
            source_name=source_name,
            latency_ms=latency,
            format="JSON"
        )
    
    def _error_response(
        self,
        error_message: str,
        source_name: str
    ) -> data_source_pb2.DataResponse:
        """构建错误响应"""
        return data_source_pb2.DataResponse(
            success=False,
            error_message=error_message,
            source_name=source_name
        )
    
    def _validate_data(
        self,
        df: pd.DataFrame,
        data_type: int
    ) -> tuple[bool, str]:
        """
        验证数据有效性
        
        Args:
            df: 待验证的 DataFrame
            data_type: 数据类型枚举值
            
        Returns:
            (is_valid, error_message)
        """
        # 获取类型名称
        type_name = data_source_pb2.DataType.Name(data_type).replace("DATA_TYPE_", "")
        rules = VALIDATION_RULES.get(type_name)
        
        if not rules:
            return True, ""
        
        if df.empty:
            return False, "Empty DataFrame"
        
        if len(df) < rules.get("min_rows", 1):
            return False, f"Too few rows: {len(df)}"
        
        required = rules.get("required_columns", [])
        missing = [c for c in required if c not in df.columns]
        if missing:
            return False, f"Missing columns: {missing}"
        
        return True, ""
    
    async def _record_stats(
        self,
        source: str,
        success: bool,
        latency_ms: int
    ) -> None:
        """
        记录数据源调用统计
        
        Args:
            source: 数据源名称
            success: 调用是否成功
            latency_ms: 延迟毫秒数
        """
        async with self._stats_lock:
            if source not in self._stats:
                self._stats[source] = SourceStats()
            
            stats = self._stats[source]
            if success:
                stats.success_count += 1
                stats.total_latency_ms += latency_ms
                stats.last_success = datetime.now()
            else:
                stats.failure_count += 1
                stats.last_failure = datetime.now()
    
    def get_stats(self) -> Dict[str, Dict]:
        """获取所有数据源统计信息"""
        return {
            source: {
                "success_count": stats.success_count,
                "failure_count": stats.failure_count,
                "success_rate": f"{stats.success_rate:.2%}",
                "avg_latency_ms": f"{stats.avg_latency_ms:.1f}",
                "last_success": stats.last_success.isoformat() if stats.last_success else None,
                "last_failure": stats.last_failure.isoformat() if stats.last_failure else None,
            }
            for source, stats in self._stats.items()
        }
    
    async def _fetch_quotes_mootdx(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """mootdx: 实时行情（委托给 handler）"""
        if not self.mootdx_client:
            logger.warning("Mootdx client not initialized")
            return pd.DataFrame()
        return await self.mootdx_client.get_quotes(codes, params)
    
    async def _fetch_quotes_easyquotation(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        easyquotation: 实时行情（降级用，委托给 handler）
        
        当 mootdx 不可用时的备选方案。
        """
        if not self.easy_handler:
            logger.warning("Easyquotation handler not initialized")
            return pd.DataFrame()
        return await self.easy_handler.get_quotes(codes, params)
    
    async def _fetch_tick_mootdx(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """mootdx: 分笔数据（委托给 handler）"""
        if not self.mootdx_client:
            logger.warning("Mootdx client not initialized")
            return pd.DataFrame()
        return await self.mootdx_client.get_tick(codes, params)
    
    async def _fetch_history_mootdx(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """mootdx: 历史K线（降级用，委托给 handler）"""
        if not self.mootdx_client:
            logger.warning("Mootdx client not initialized")
            return pd.DataFrame()
        return await self.mootdx_client.get_history(codes, params)
    
    # === 云端 API 方法 ===
    
    async def _fetch_history_baostock(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """baostock: 历史K线"""
        if not codes:
            raise ValueError("No code specified for HISTORY")
        
        code = codes[0]
        start_date = params.get("start_date", HistoryDefaults.get_start_date())
        end_date = params.get("end_date", HistoryDefaults.get_end_date())
        frequency = params.get("frequency", HistoryDefaults.FREQUENCY)
        adjust = params.get("adjust", HistoryDefaults.ADJUST)
        
        endpoint = f"/api/v1/history/kline/{code}"
        query_params = {
            "start_date": start_date,
            "end_date": end_date,
            "frequency": frequency,
            "adjust": adjust
        }
        
        return await self.cloud_client.fetch_baostock(endpoint, query_params)
    
    async def _fetch_ranking_akshare(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """akshare: 榜单数据"""
        ranking_type = params.get("ranking_type", QueryDefaults.RANKING_DEFAULT_TYPE)
        endpoint = f"/api/v1/rank/{ranking_type}"
        return await self.cloud_client.fetch_akshare(endpoint)
    
    async def _fetch_sector_pywencai(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """pywencai: 板块数据"""
        query = params.get("query", QueryDefaults.PYWENCAI_DEFAULT_QUERY)
        perpage = int(params.get("perpage", QueryDefaults.PYWENCAI_DEFAULT_PERPAGE))
        return await self.cloud_client.fetch_pywencai(query, perpage)
    
    async def _fetch_finance_akshare(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """akshare: 财务数据"""
        if not codes:
            raise ValueError("No code specified for FINANCE")
        code = codes[0]
        endpoint = f"/api/v1/finance/{code}"
        return await self.cloud_client.fetch_akshare(endpoint, params)
    
    async def _fetch_finance_baostock(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        baostock: 财务数据（降级用）
        
        当 akshare 不可用时的备选方案。
        注意: baostock 财务数据字段可能与 akshare 不同，需要字段映射。
        """
        if not codes:
            raise ValueError("No code specified for FINANCE")
        code = codes[0]
        endpoint = f"/api/v1/finance/profit/{code}"
        return await self.cloud_client.fetch_baostock(endpoint)
    
    async def _fetch_valuation_akshare(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """akshare: 估值数据"""
        if not codes:
            raise ValueError("No code specified for VALUATION")
        code = codes[0]
        endpoint = f"/api/v1/valuation/{code}"
        return await self.cloud_client.fetch_akshare(endpoint)
    
    async def _fetch_index_baostock(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """baostock: 指数成分"""
        if not codes:
            raise ValueError("No code specified for INDEX")
        index_code = codes[0]
        date = params.get("date", "")
        endpoint = f"/api/v1/index/cons/{index_code}"
        query_params = {"date": date} if date else None
        return await self.cloud_client.fetch_baostock(endpoint, query_params)
    
    async def _fetch_industry_baostock(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """baostock: 行业数据"""
        symbol = codes[0] if codes else None
        date = params.get("date", "")
        endpoint = "/api/v1/industry/classify"
        query_params = {}
        if symbol:
            query_params["symbol"] = symbol
        if date:
            query_params["date"] = date
        return await self.cloud_client.fetch_baostock(
            endpoint,
            query_params if query_params else None
        )
    
    async def _fetch_industry_akshare(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        akshare: 行业数据（降级用）
        
        当 baostock 不可用时的备选方案。
        """
        symbol = codes[0] if codes else None
        if not symbol:
            # 获取行业列表
            endpoint = "/api/v1/industry/list"
            return await self.cloud_client.fetch_akshare(endpoint)
        else:
            # 获取个股行业信息
            endpoint = f"/api/v1/industry/stock/{symbol}"
            return await self.cloud_client.fetch_akshare(endpoint)
    
    async def _fetch_dragon_tiger_akshare(
        self,
        codes: List[str],
        params: Dict[str, Any]
    ) -> pd.DataFrame:
        """
        akshare: 龙虎榜数据
        
        获取沪深股市龙虎榜交易明细，包括：
        - 上榜股票
        - 买入/卖出营业部
        - 交易金额
        
        Args:
            codes: 股票代码列表（可选，不填返回全部）
            params: 查询参数
                - date: 日期 (YYYY-MM-DD)，默认昨天
                - market: 市场类型 ("沪深", "上海", "深圳")
        
        Returns:
            DataFrame 包含:
                - code: 股票代码
                - name: 股票名称  
                - close_price: 收盘价
                - change_pct: 涨跌幅
                - lhb_reason: 上榜原因
                - buy_total: 买入总额
                - sell_total: 卖出总额
        
        Example:
            >>> params = {"date": "2025-12-17", "market": "沪深"}
            >>> df = await self._fetch_dragon_tiger_akshare(codes=[], params=params)
        """
        # 获取参数（使用配置默认值）
        date = params.get("date", DragonTigerDefaults.get_default_date())
        market = params.get("market", DragonTigerDefaults.MARKET)
        
        # 构建 API 请求
        endpoint = "/api/v1/dragon_tiger/daily"
        query_params = {
            "date": date,
            "market": market
        }
        
        # 如果指定了股票代码，添加过滤
        if codes:
            query_params["codes"] = ",".join(codes)
        
        # 调用云端 API
        df = await self.cloud_client.fetch_akshare(endpoint, query_params)
        
        # 如果有股票代码过滤，在本地再次过滤确保准确性
        if codes and not df.empty and 'code' in df.columns:
            df = df[df['code'].isin(codes)]
        
        return df
    
    async def GetCapabilities(
        self,
        request: data_source_pb2.Empty,
        context: grpc.aio.ServicerContext
    ) -> data_source_pb2.Capabilities:
        """gRPC: 获取服务能力"""
        return data_source_pb2.Capabilities(
            supported_types=list(self.ROUTING_TABLE.keys()),
            priority=100,
            version="2.0.0-hybrid"
        )
    
    async def HealthCheck(
        self,
        request: data_source_pb2.Empty,
        context: grpc.aio.ServicerContext
    ) -> data_source_pb2.HealthStatus:
        """gRPC: 健康检查"""
        # 检查所有数据源状态
        healthy = all([
            self.mootdx_client is not None,
            self.easyquotation_client is not None,
            self.cloud_client is not None
        ])
        
        message = "All datasources healthy" if healthy else "Some datasources unavailable"
        
        return data_source_pb2.HealthStatus(
            healthy=healthy,
            message=message
        )
