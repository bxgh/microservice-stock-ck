#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
分笔数据模型
定义股票分笔交易数据结构和相关模型
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, time
from .base_models import ApiResponse, PaginationInfo


class TickData(BaseModel):
    """单条分笔数据"""
    time: datetime = Field(..., description="成交时间")
    price: float = Field(..., description="成交价格", gt=0)
    volume: int = Field(..., description="成交量", ge=0)
    amount: float = Field(..., description="成交额", ge=0)
    direction: str = Field(..., description="买卖方向", pattern="^(B|S|N)$")  # B=买盘 S=卖盘 N=中性
    code: str = Field(..., description="股票代码")
    date: datetime = Field(..., description="交易日期")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TickDataRequest(BaseModel):
    """分笔数据查询请求"""
    stock_code: str = Field(..., description="股票代码", example="000001")
    date: datetime = Field(..., description="查询日期", example="2025-11-18")
    market: str = Field("SZ", description="市场代码", pattern="^(SH|SZ|BJ)$")
    include_auction: bool = Field(True, description="是否包含集合竞价")

    class Config:
        json_encoders = {
            datetime: lambda v: v.date().isoformat()
        }


class TickDataBatchRequest(BaseModel):
    """批量分笔数据查询请求"""
    stock_codes: List[str] = Field(..., description="股票代码列表", min_items=1, max_items=100)
    date: datetime = Field(..., description="查询日期")
    include_auction: bool = Field(True, description="是否包含集合竞价")

    class Config:
        json_encoders = {
            datetime: lambda v: v.date().isoformat()
        }


class TickDataResponse(ApiResponse):
    """分笔数据响应"""
    data: List[TickData] = Field(..., description="分笔数据列表")
    summary: Optional[Dict[str, Any]] = Field(None, description="数据摘要信息")


class TickDataBatchResponse(ApiResponse):
    """批量分笔数据响应"""
    data: Dict[str, List[TickData]] = Field(..., description="按股票代码分组的分笔数据")
    success_count: int = Field(..., description="成功获取的股票数量")
    failed_count: int = Field(..., description="获取失败的股票数量")
    failed_stocks: List[str] = Field(default_factory=list, description="失败的股票代码列表")


class TickDataSummary(BaseModel):
    """分笔数据摘要"""
    stock_code: str = Field(..., description="股票代码")
    date: datetime = Field(..., description="交易日期")
    total_volume: int = Field(..., description="总成交量")
    total_amount: float = Field(..., description="总成交额")
    open_price: float = Field(..., description="开盘价")
    close_price: float = Field(..., description="收盘价")
    high_price: float = Field(..., description="最高价")
    low_price: float = Field(..., description="最低价")
    avg_price: float = Field(..., description="平均成交价")
    tick_count: int = Field(..., description="分笔数量")
    auction_price: Optional[float] = Field(None, description="集合竞价价格")
    auction_volume: Optional[int] = Field(None, description="集合竞价成交量")

    class Config:
        json_encoders = {
            datetime: lambda v: v.date().isoformat()
        }


class DataSourceStatus(BaseModel):
    """数据源状态"""
    source_name: str = Field(..., description="数据源名称")
    is_connected: bool = Field(..., description="是否已连接")
    last_check: datetime = Field(..., description="最后检查时间")
    available_servers: List[str] = Field(default_factory=list, description="可用服务器列表")
    response_time: Optional[float] = Field(None, description="响应时间(毫秒)")
    error_message: Optional[str] = Field(None, description="错误信息")


class TickDataFilter(BaseModel):
    """分笔数据筛选条件"""
    stock_codes: Optional[List[str]] = Field(None, description="股票代码筛选")
    exchanges: Optional[List[str]] = Field(None, description="交易所筛选")
    date_range: Optional[Dict[str, datetime]] = Field(None, description="日期范围筛选")
    price_range: Optional[Dict[str, float]] = Field(None, description="价格范围筛选")
    volume_threshold: Optional[int] = Field(None, description="成交量阈值")
    include_auction: Optional[bool] = Field(None, description="是否包含集合竞价")


class TickDataStatistics(BaseModel):
    """分笔数据统计"""
    date: datetime = Field(..., description="统计日期")
    total_stocks: int = Field(..., description="总股票数")
    success_count: int = Field(..., description="成功获取数量")
    failed_count: int = Field(..., description="获取失败数量")
    total_ticks: int = Field(..., description="总分笔数量")
    avg_ticks_per_stock: float = Field(..., description="平均每只股票分笔数")
    total_volume: int = Field(..., description="总成交量")
    total_amount: float = Field(..., description="总成交额")
    processing_time: float = Field(..., description="处理耗时(秒)")
    data_sources: Dict[str, DataSourceStatus] = Field(..., description="数据源状态")

    class Config:
        json_encoders = {
            datetime: lambda v: v.date().isoformat()
        }


# 分笔数据适配器
class TickDataAdapter:
    """分笔数据适配器，用于转换不同数据源的格式"""

    @staticmethod
    def from_tdx(tdx_data: Dict[str, Any], stock_code: str, date: datetime) -> TickData:
        """从通达信格式转换为内部格式"""
        return TickData(
            time=date.combine(date.date(),
                           time.fromisoformat(tdx_data.get('time', '09:30:00'))),
            price=float(tdx_data.get('price', 0)),
            volume=int(tdx_data.get('volume', 0)),
            amount=float(tdx_data.get('amount', 0)),
            direction=tdx_data.get('direction', 'N'),
            code=stock_code,
            date=date
        )

    @staticmethod
    def from_akshare(ak_data: Dict[str, Any], stock_code: str, date: datetime) -> TickData:
        """从AKShare格式转换为内部格式"""
        return TickData(
            time=datetime.strptime(ak_data.get('time', ''), '%H:%M:%S').replace(
                year=date.year, month=date.month, day=date.day),
            price=float(ak_data.get('price', 0)),
            volume=int(ak_data.get('volume', 0)),
            amount=float(ak_data.get('amount', 0)),
            direction=ak_data.get('direction', 'N'),
            code=stock_code,
            date=date
        )

    @staticmethod
    def calculate_summary(tick_data: List[TickData], stock_code: str, date: datetime) -> TickDataSummary:
        """计算分笔数据摘要"""
        if not tick_data:
            return TickDataSummary(
                stock_code=stock_code,
                date=date,
                total_volume=0,
                total_amount=0.0,
                open_price=0.0,
                close_price=0.0,
                high_price=0.0,
                low_price=0.0,
                avg_price=0.0,
                tick_count=0
            )

        prices = [tick.price for tick in tick_data]
        volumes = [tick.volume for tick in tick_data]
        amounts = [tick.amount for tick in tick_data]

        # 找出集合竞价数据 (09:25:00)
        auction_data = [tick for tick in tick_data if tick.time.time() == time(9, 25, 0)]
        auction_price = auction_data[0].price if auction_data else None
        auction_volume = sum(tick.volume for tick in auction_data) if auction_data else None

        return TickDataSummary(
            stock_code=stock_code,
            date=date,
            total_volume=sum(volumes),
            total_amount=sum(amounts),
            open_price=prices[0] if prices else 0.0,
            close_price=prices[-1] if prices else 0.0,
            high_price=max(prices) if prices else 0.0,
            low_price=min(prices) if prices else 0.0,
            avg_price=sum(amounts) / sum(volumes) if sum(volumes) > 0 else 0.0,
            tick_count=len(tick_data),
            auction_price=auction_price,
            auction_volume=auction_volume
        )