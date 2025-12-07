#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GuaranteedSuccessStrategy核心引擎模型
基于真正100%成功策略的数据结构定义
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, time
from pydantic import BaseModel, Field, model_validator
from enum import Enum


class StrategyStatus(str, Enum):
    """策略状态枚举"""
    PENDING = "pending"
    SEARCHING = "searching"
    FOUND = "found"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class SearchStep(BaseModel):
    """搜索步骤模型"""
    step_id: int = Field(..., description="步骤ID")
    description: str = Field(..., description="步骤描述")
    start_pos: int = Field(..., description="起始位置")
    offset: int = Field(..., description="偏移量")
    found_0925: bool = Field(default=False, description="是否找到09:25数据")
    earliest_time: Optional[str] = Field(default=None, description="此批次最早时间")
    record_count: int = Field(default=0, description="记录数量")
    execution_time: float = Field(default=0.0, description="执行时间(秒)")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class SuccessResult(BaseModel):
    """成功结果数据结构"""
    symbol: str = Field(..., min_length=1, max_length=10, description="股票代码")
    name: str = Field(..., min_length=1, max_length=50, description="股票名称")
    success: bool = Field(..., description="是否成功")
    earliest_time: str = Field(..., min_length=1, description="最早时间")
    latest_time: str = Field(..., min_length=1, description="最晚时间")
    record_count: int = Field(..., ge=0, description="记录数量")
    strategy_used: str = Field(..., min_length=1, description="使用的策略")
    execution_time: float = Field(..., ge=0, description="执行时间(秒)")
    target_achieved: bool = Field(..., description="是否达成目标时间")
    data_quality_score: float = Field(default=0.0, ge=0, le=1, description="数据质量评分")
    search_steps: List[SearchStep] = Field(default_factory=list, description="搜索步骤详情")

    # 新增字段用于更好的分析
    market: str = Field(default="SZ", description="交易所")
    date: str = Field(..., min_length=8, max_length=8, description="查询日期")
    data_source: str = Field(default="tongdaxin", description="数据源")
    retry_count: int = Field(default=0, ge=0, description="重试次数")
    error_details: Optional[str] = Field(default=None, description="详细错误信息")

    @model_validator(mode='after')
    def validate_symbol_format(self):
        """验证股票代码格式"""
        if not self.symbol or len(self.symbol.strip()) == 0:
            raise ValueError("股票代码不能为空")
        if not self.symbol.isalnum():
            raise ValueError("股票代码只能包含字母和数字")
        return self


class BatchExecutionRequest(BaseModel):
    """批量执行请求模型"""
    stock_list: List[Dict[str, str]] = Field(..., min_items=1, description="股票列表 [{'symbol': '000001', 'name': '平安银行'}]")
    date: str = Field(..., min_length=8, max_length=8, description="查询日期 (YYYYMMDD)")
    target_time: str = Field(default="09:25", pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", description="目标时间 (HH:MM)")
    max_concurrent: int = Field(default=3, ge=1, le=20, description="最大并发数")
    timeout_per_stock: int = Field(default=120, ge=30, description="每只股票超时时间(秒)")
    retry_attempts: int = Field(default=2, ge=0, le=5, description="重试次数")

    @model_validator(mode='after')
    def validate_stock_list_format(self):
        """验证股票列表格式"""
        if not self.stock_list:
            raise ValueError("股票列表不能为空")

        for i, stock in enumerate(self.stock_list):
            if not isinstance(stock, dict):
                raise ValueError(f"股票列表第{i+1}项必须是字典")

            if 'symbol' not in stock or 'name' not in stock:
                raise ValueError(f"股票列表第{i+1}项必须包含symbol和name字段")

            symbol = stock['symbol']
            name = stock['name']

            if not symbol or len(symbol.strip()) == 0:
                raise ValueError(f"股票列表第{i+1}项的symbol不能为空")

            if not name or len(name.strip()) == 0:
                raise ValueError(f"股票列表第{i+1}项的name不能为空")

            if not symbol.isalnum():
                raise ValueError(f"股票代码 {symbol} 只能包含字母和数字")

        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "stock_list": [
                    {"symbol": "000001", "name": "平安银行"},
                    {"symbol": "000002", "name": "万科A"}
                ],
                "date": "20251119",
                "target_time": "09:25",
                "max_concurrent": 3,
                "timeout_per_stock": 120,
                "retry_attempts": 2
            }
        }
    }


class BatchExecutionResult(BaseModel):
    """批量执行结果模型"""
    request_id: str = Field(..., description="请求ID")
    total_stocks: int = Field(..., description="总股票数")
    successful_stocks: int = Field(..., description="成功股票数")
    perfect_stocks: int = Field(..., description="完美达成股票数 (09:25)")
    failed_stocks: int = Field(..., description="失败股票数")
    success_rate: float = Field(..., ge=0, le=1, description="成功率")
    perfect_rate: float = Field(..., ge=0, le=1, description="完美率")
    total_execution_time: float = Field(..., description="总执行时间(秒)")
    average_time_per_stock: float = Field(..., description="平均每只股票耗时(秒)")
    target_time: str = Field(..., description="目标时间")
    date: str = Field(..., description="查询日期")
    results: List[SuccessResult] = Field(..., description="详细结果列表")

    # 性能统计
    total_data_records: int = Field(default=0, description="总数据记录数")
    average_records_per_stock: float = Field(default=0.0, description="平均每只股票记录数")
    fastest_execution: float = Field(default=float('inf'), description="最快执行时间")
    slowest_execution: float = Field(default=0.0, description="最慢执行时间")

    # 策略统计
    most_used_strategy: str = Field(default="", description="最常用策略")
    strategy_effectiveness: Dict[str, float] = Field(default_factory=dict, description="策略有效性统计")

    # 错误统计
    error_summary: Dict[str, int] = Field(default_factory=dict, description="错误类型统计")

    execution_start_time: datetime = Field(..., description="执行开始时间")
    execution_end_time: datetime = Field(..., description="执行结束时间")


class SearchMatrixConfig(BaseModel):
    """搜索矩阵配置模型"""
    target_time: str = Field(default="09:25", description="目标时间")
    matrix_steps: List[Dict[str, Any]] = Field(..., description="搜索矩阵步骤")

    model_config = {
        "json_schema_extra": {
            "example": {
                "target_time": "09:25",
                "matrix_steps": [
                    {"start_pos": 3500, "offset": 800, "description": "万科A前区域", "priority": 1},
                    {"start_pos": 4000, "offset": 500, "description": "万科A原成功", "priority": 1}
                ]
            }
        }
    }


class StrategyExecutionStats(BaseModel):
    """策略执行统计模型"""
    total_executions: int = Field(default=0, description="总执行次数")
    successful_executions: int = Field(default=0, description="成功执行次数")
    average_execution_time: float = Field(default=0.0, description="平均执行时间")
    last_execution_time: Optional[datetime] = Field(default=None, description="最后执行时间")
    success_rate: float = Field(default=0.0, description="成功率")

    # 按股票类型统计
    stats_by_market: Dict[str, int] = Field(default_factory=dict, description="按交易所统计")

    # 按时间段统计
    stats_by_time_period: Dict[str, int] = Field(default_factory=dict, description="按时间段统计")

    # 错误统计
    error_count: int = Field(default=0, description="错误次数")
    common_errors: List[str] = Field(default_factory=list, description="常见错误")


class GuaranteedStrategyConfig(BaseModel):
    """保证策略配置模型"""
    # 搜索配置
    target_time: str = Field(default="09:25", description="目标时间")
    max_search_steps: int = Field(default=15, ge=1, description="最大搜索步数")
    smart_stop_enabled: bool = Field(default=True, description="启用智能停止")
    ensure_data_completeness: bool = Field(default=True, description="确保数据完整性")

    # 性能配置
    max_concurrent_stocks: int = Field(default=5, ge=1, le=20, description="最大并发股票数")
    timeout_per_stock: int = Field(default=120, ge=30, description="每只股票超时时间(秒)")
    retry_attempts: int = Field(default=3, ge=0, description="重试次数")
    delay_between_requests: float = Field(default=0.1, ge=0, description="请求间延迟(秒)")

    # 数据质量配置
    enable_deduplication: bool = Field(default=True, description="启用去重")
    enable_data_validation: bool = Field(default=True, description="启用数据验证")
    min_data_quality_score: float = Field(default=0.8, ge=0, le=1, description="最小数据质量评分")

    # 日志配置
    enable_detailed_logging: bool = Field(default=True, description="启用详细日志")
    log_execution_steps: bool = Field(default=True, description="记录执行步骤")

    # 输出配置
    save_successful_data: bool = Field(default=False, description="保存成功数据")
    output_directory: str = Field(default="./results", description="输出目录")
    enable_performance_monitoring: bool = Field(default=True, description="启用性能监控")


class TickDataValidationResult(BaseModel):
    """分笔数据验证结果模型"""
    is_valid: bool = Field(..., description="数据是否有效")
    earliest_time: str = Field(..., description="最早时间")
    latest_time: str = Field(..., description="最晚时间")
    target_achieved: bool = Field(..., description="是否达成目标时间")
    record_count: int = Field(..., description="记录数量")
    quality_score: float = Field(..., ge=0, le=1, description="数据质量评分")

    # 验证详情
    time_coverage_complete: bool = Field(default=False, description="时间覆盖是否完整")
    no_duplicate_records: bool = Field(default=False, description="无重复记录")
    data_format_correct: bool = Field(default=False, description="数据格式是否正确")
    expected_columns_present: bool = Field(default=False, description="期望列是否存在")

    # 数据统计
    time_gaps_count: int = Field(default=0, description="时间间隔数量")
    duplicate_count: int = Field(default=0, description="重复记录数量")
    abnormal_records_count: int = Field(default=0, description="异常记录数量")

    validation_errors: List[str] = Field(default_factory=list, description="验证错误列表")


# 导出所有模型
__all__ = [
    "StrategyStatus",
    "SearchStep",
    "SuccessResult",
    "BatchExecutionRequest",
    "BatchExecutionResult",
    "SearchMatrixConfig",
    "StrategyExecutionStats",
    "GuaranteedStrategyConfig",
    "TickDataValidationResult"
]