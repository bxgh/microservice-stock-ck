#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
股票数据模型
定义股票基础数据结构和相关模型
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from .base_models import ApiResponse, PaginationInfo


class StockCodeMapping(BaseModel):
    """股票代码映射信息"""
    standard: str = Field(..., description="标准代码")
    tushare: str = Field(..., description="Tushare代码")
    akshare: str = Field(..., description="AKShare代码")
    tonghua_shun: str = Field(..., description="同花顺代码")
    wind: str = Field(..., description="Wind代码")
    east_money: str = Field(..., description="东方财富代码")


class StockInfo(BaseModel):
    """股票基础信息"""
    stock_code: str = Field(..., description="股票代码", example="000001")
    stock_name: str = Field(..., description="股票名称", example="平安银行")
    exchange: str = Field(..., description="交易所", example="SZ", pattern="^(SH|SZ|BJ)$")
    asset_type: str = Field("stock", description="资产类型", example="stock")
    is_active: bool = Field(True, description="是否活跃")
    code_mappings: StockCodeMapping = Field(..., description="多格式代码映射")
    list_date: Optional[datetime] = Field(None, description="上市日期")
    delist_date: Optional[datetime] = Field(None, description="退市日期")
    data_source: Optional[str] = Field(None, description="数据来源")
    last_updated: Optional[datetime] = Field(None, description="最后更新时间")
    # Enhanced Info (EPIC-002)
    industry: Optional[str] = Field(None, description="所属行业")
    industry_code: Optional[str] = Field(None, description="行业代码") # New field
    sector: Optional[str] = Field(None, description="所属板块")
    
    # Enhanced Info (EPIC-005)
    market_cap: Optional[float] = Field(None, description="总市值(亿元)")
    turnover_ratio: Optional[float] = Field(None, description="换手率(%)")
    avg_turnover_20d: Optional[float] = Field(None, description="20日平均成交额(万元)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class StockListRequest(BaseModel):
    """股票列表查询请求"""
    exchange: Optional[str] = Field(None, description="交易所筛选", pattern="^(SH|SZ|BJ)$")
    asset_type: Optional[str] = Field(None, description="资产类型筛选")
    is_active: Optional[bool] = Field(None, description="活跃状态筛选")
    name_search: Optional[str] = Field(None, description="股票名称搜索", min_length=1)
    skip: int = Field(0, description="跳过数量", ge=0)
    limit: int = Field(100, description="返回数量", ge=1, le=1000)


class StockListResponse(ApiResponse):
    """股票列表响应"""
    data: List[StockInfo] = Field(..., description="股票列表")
    pagination: PaginationInfo = Field(..., description="分页信息")


class StockDetailResponse(ApiResponse):
    """股票详情响应"""
    data: StockInfo = Field(..., description="股票详情")


class StockSearchRequest(BaseModel):
    """股票搜索请求"""
    query: str = Field(..., description="搜索关键词", min_length=1, max_length=50)
    limit: int = Field(20, description="返回数量", ge=1, le=100)


class StockBatchRequest(BaseModel):
    """批量股票查询请求"""
    stock_codes: List[str] = Field(..., description="股票代码列表", min_items=1, max_items=100)


class StockMappingsResponse(ApiResponse):
    """股票代码映射响应"""
    data: StockCodeMapping = Field(..., description="代码映射信息")


class StockExportRequest(BaseModel):
    """股票数据导出请求"""
    format: str = Field("json", description="导出格式", pattern="^(json|csv)$")
    exchange: Optional[str] = Field(None, description="交易所筛选")
    asset_type: Optional[str] = Field(None, description="资产类型筛选")
    is_active: Optional[bool] = Field(None, description="活跃状态筛选")


class CacheStatusResponse(ApiResponse):
    """缓存状态响应"""
    data: Dict[str, Any] = Field(..., description="缓存状态信息")


class StockFilter(BaseModel):
    """股票筛选条件"""
    exchange: Optional[str] = Field(None, description="交易所")
    asset_type: Optional[str] = Field(None, description="资产类型")
    is_active: Optional[bool] = Field(None, description="活跃状态")
    name_contains: Optional[str] = Field(None, description="名称包含")
    list_date_after: Optional[datetime] = Field(None, description="上市日期晚于")
    list_date_before: Optional[datetime] = Field(None, description="上市日期早于")


# 外部API响应模型
class ExternalStockResponse(BaseModel):
    """外部API股票响应格式"""
    standard_code: str = Field(..., description="标准化代码")
    name: str = Field(..., description="股票名称")
    exchange: str = Field(..., description="交易所")
    security_type: str = Field(..., description="证券类型")
    is_active: bool = Field(..., description="是否活跃")
    formats: Dict[str, str] = Field(..., description="多格式代码")
    list_date: Optional[datetime] = Field(None, description="上市日期")
    delist_date: Optional[datetime] = Field(None, description="退市日期")
    data_source: Optional[str] = Field(None, description="数据来源")
    last_updated: Optional[datetime] = Field(None, description="最后更新时间")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ExternalStockListResponse(BaseModel):
    """外部API股票列表响应"""
    items: List[ExternalStockResponse] = Field(..., description="股票列表")
    total: int = Field(..., description="总数量")
    skip: int = Field(..., description="跳过数量")
    limit: int = Field(..., description="返回数量")
    has_more: bool = Field(..., description="是否有更多数据")


# 数据适配器
class StockDataAdapter:
    """股票数据适配器，将外部API格式转换为内部格式"""

    @staticmethod
    def from_external(external_stock: ExternalStockResponse) -> StockInfo:
        """将外部API格式转换为内部格式"""
        return StockInfo(
            stock_code=external_stock.standard_code,
            stock_name=external_stock.name,
            exchange=external_stock.exchange,
            asset_type=external_stock.security_type,
            is_active=external_stock.is_active,
            code_mappings=StockCodeMapping(
                standard=external_stock.formats.get("standard", external_stock.standard_code),
                tushare=external_stock.formats.get("tushare", ""),
                akshare=external_stock.formats.get("akshare", external_stock.standard_code),
                tonghua_shun=external_stock.formats.get("tonghua_shun", ""),
                wind=external_stock.formats.get("wind", ""),
                east_money=external_stock.formats.get("east_money", "")
            ),
            list_date=external_stock.list_date,
            delist_date=external_stock.delist_date,
            data_source=external_stock.data_source,
            last_updated=external_stock.last_updated
        )

    @staticmethod
    def from_external_list(external_stocks: List[ExternalStockResponse]) -> List[StockInfo]:
        """批量转换外部API格式为内部格式"""
        return [StockDataAdapter.from_external(stock) for stock in external_stocks]


# 缓存键生成器
class CacheKeyGenerator:
    """缓存键生成器"""

    @staticmethod
    def stocks_all() -> str:
        """全市场股票列表缓存键"""
        return "stocks:all"

    @staticmethod
    def stocks_by_exchange(exchange: str) -> str:
        """按交易所股票列表缓存键"""
        return f"stocks:exchange:{exchange}"

    @staticmethod
    def stock_detail(stock_code: str) -> str:
        """单只股票详情缓存键"""
        return f"stock:{stock_code}"

    @staticmethod
    def stock_mappings(stock_code: str) -> str:
        """股票代码映射缓存键"""
        return f"stock:{stock_code}:mappings"

    @staticmethod
    def stock_search(query: str) -> str:
        """股票搜索结果缓存键"""
        return f"stocks:search:{query}"

    @staticmethod
    def stats_total_count() -> str:
        """股票总数统计缓存键"""
        return "stats:total_count"

    @staticmethod
    def stats_exchange_count() -> str:
        """各交易所股票统计缓存键"""
        return "stats:exchange_count"