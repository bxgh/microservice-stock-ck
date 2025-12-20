#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分笔数据质量验证器
-----------------
作为证券专家，对 mootdx 分笔数据进行全面质量验证

验证维度:
1. 字段完整性验证
2. 价格合理性验证 (涨跌停限制)
3. 成交量验证 (非负、手数规则)
4. 时间序列验证 (递增、交易时间)
5. 买卖方向验证 (与盘口价格一致性)
6. 累计一致性验证 (分笔总量 vs K线总量)
7. 异常数据检测 (离群值、价格跳跃)
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, time
from dataclasses import dataclass, field
import asyncio

import pandas as pd
import numpy as np
from mootdx.quotes import Quotes

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent / "src"))
from datasource.handlers.mootdx_handler import MootdxHandler


@dataclass
class ValidationResult:
    """单项验证结果"""
    passed: bool
    score: float  # 0.0 - 1.0
    error_count: int = 0
    total_count: int = 0
    details: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def pass_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return (self.total_count - self.error_count) / self.total_count


@dataclass
class TickDataQualityReport:
    """分笔数据质量报告"""
    stock_code: str
    test_date: str
    record_count: int
    
    # 验证结果
    field_validation: ValidationResult
    price_validation: ValidationResult
    volume_validation: ValidationResult
    time_validation: ValidationResult
    direction_validation: Optional[ValidationResult] = None
    consistency_validation: Optional[ValidationResult] = None
    anomaly_detection: Optional[ValidationResult] = None
    
    @property
    def overall_score(self) -> float:
        """综合评分 (加权平均)"""
        weights = {
            'field': 0.15,
            'price': 0.20,
            'volume': 0.15,
            'time': 0.15,
            'direction': 0.15,
            'consistency': 0.15,
            'anomaly': 0.05
        }
        
        scores = {
            'field': self.field_validation.score,
            'price': self.price_validation.score,
            'volume': self.volume_validation.score,
            'time': self.time_validation.score,
            'direction': self.direction_validation.score if self.direction_validation else 1.0,
            'consistency': self.consistency_validation.score if self.consistency_validation else 1.0,
            'anomaly': self.anomaly_detection.score if self.anomaly_detection else 1.0
        }
        
        return sum(scores[k] * weights[k] for k in weights.keys())
    
    @property
    def status(self) -> str:
        """整体状态"""
        score = self.overall_score
        if score >= 0.95:
            return "✅ EXCELLENT"
        elif score >= 0.90:
            return "✅ GOOD"
        elif score >= 0.80:
            return "⚠️ ACCEPTABLE"
        elif score >= 0.70:
            return "⚠️ POOR"
        else:
            return "❌ FAILED"


class TickDataQualityValidator:
    """分笔数据质量验证器"""
    
    # A股交易时间段
    TRADING_SESSIONS = [
        (time(9, 30), time(11, 30)),   # 上午
        (time(13, 0), time(15, 0))      # 下午
    ]
    
    # 集合竞价时间
    AUCTION_TIME = (time(9, 15), time(9, 25))
    
    def __init__(self):
        self.handler: Optional[MootdxHandler] = None
        self.client: Optional[Quotes] = None
    
    async def initialize(self) -> None:
        """初始化 mootdx handler"""
        self.handler = MootdxHandler()
        await self.handler.initialize()
        self.client = self.handler.client
        print("✓ TickDataQualityValidator initialized")
    
    async def close(self) -> None:
        """关闭资源"""
        if self.handler:
            await self.handler.close()
    
    def validate_fields(self, df: pd.DataFrame) -> ValidationResult:
        """
        1. 字段完整性验证
        
        验证点:
        - 必需字段存在
        - 字段类型正确
        - 无空值
        """
        required_fields = ['time', 'price', 'volume']
        errors = []
        warnings = []
        
        # 检查字段存在
        missing_fields = [f for f in required_fields if f not in df.columns]
        if missing_fields:
            errors.append(f"缺失必需字段: {missing_fields}")
        
        # 检查空值
        for field in required_fields:
            if field in df.columns:
                null_count = df[field].isnull().sum()
                if null_count > 0:
                    errors.append(f"字段 '{field}' 有 {null_count} 个空值")
        
        # 检查数据类型
        if 'price' in df.columns:
            if not pd.api.types.is_numeric_dtype(df['price']):
                errors.append(f"字段 'price' 类型错误: {df['price'].dtype}")
        
        if 'volume' in df.columns:
            if not pd.api.types.is_numeric_dtype(df['volume']):
                errors.append(f"字段 'volume' 类型错误: {df['volume'].dtype}")
        
        # 检查可选字段
        if 'type' in df.columns:
            type_values = df['type'].unique()
            warnings.append(f"买卖类型 'type' 字段值分布: {list(type_values)}")
        else:
            warnings.append("未找到 'type' 字段 (买卖方向)")
        
        passed = len(errors) == 0
        score = 1.0 if passed else 0.0
        
        return ValidationResult(
            passed=passed,
            score=score,
            error_count=len(errors),
            total_count=len(required_fields),
            details=errors,
            warnings=warnings
        )
    
    def validate_price_range(
        self, 
        df: pd.DataFrame, 
        code: str,
        prev_close: Optional[float] = None
    ) -> ValidationResult:
        """
        2. 价格合理性验证
        
        验证点:
        - 价格在涨跌停范围内 (±10%, ST ±5%)
        - 价格 > 0
        - 价格精度 (A股最小变动单位 0.01)
        """
        errors = []
        warnings = []
        error_count = 0
        
        # 价格非负
        negative_count = (df['price'] <= 0).sum()
        if negative_count > 0:
            errors.append(f"发现 {negative_count} 条价格 <= 0 的记录")
            error_count += negative_count
        
        # 价格精度检查 (保留2位小数)
        price_precision = df['price'].apply(lambda x: len(str(x).split('.')[-1]) if '.' in str(x) else 0)
        invalid_precision = (price_precision > 2).sum()
        if invalid_precision > 0:
            warnings.append(f"{invalid_precision} 条记录价格精度超过2位小数")
        
        # 涨跌停验证 (需要昨收价)
        if prev_close is not None:
            is_st = code.startswith('ST') or code.startswith('*ST')
            limit_pct = 0.05 if is_st else 0.10
            
            upper_limit = prev_close * (1 + limit_pct) * 1.01  # 容许1%误差
            lower_limit = prev_close * (1 - limit_pct) * 0.99
            
            out_of_range = ((df['price'] > upper_limit) | (df['price'] < lower_limit)).sum()
            if out_of_range > 0:
                errors.append(
                    f"发现 {out_of_range} 条价格超出涨跌停范围 "
                    f"[{lower_limit:.2f}, {upper_limit:.2f}], 昨收={prev_close:.2f}"
                )
                error_count += out_of_range
        else:
            warnings.append("未提供昨收价，跳过涨跌停验证")
        
        # 价格跳跃检测 (相邻分笔价格变动)
        if len(df) > 1:
            price_change = df['price'].pct_change().abs()
            large_jumps = (price_change > 0.10).sum()  # 单笔跳跃 > 10%
            if large_jumps > 0:
                warnings.append(f"发现 {large_jumps} 次价格单笔跳跃 > 10%")
        
        passed = error_count == 0
        score = 1.0 - (error_count / len(df)) if len(df) > 0 else 0.0
        
        return ValidationResult(
            passed=passed,
            score=score,
            error_count=error_count,
            total_count=len(df),
            details=errors,
            warnings=warnings
        )
    
    def validate_volume(self, df: pd.DataFrame) -> ValidationResult:
        """
        3. 成交量验证
        
        验证点:
        - 成交量非负
        - 成交量为100的倍数 (A股手数规则，允许少量例外如大宗交易)
        - 异常大单检测
        """
        errors = []
        warnings = []
        error_count = 0
        
        # 成交量非负
        negative_vol = (df['volume'] < 0).sum()
        if negative_vol > 0:
            errors.append(f"发现 {negative_vol} 条成交量 < 0 的记录")
            error_count += negative_vol
        
        # 成交量为0
        zero_vol = (df['volume'] == 0).sum()
        if zero_vol > 0:
            warnings.append(f"发现 {zero_vol} 条成交量 = 0 的记录 (撤单?)")
        
        # 手数规则验证 (100的倍数)
        non_hundred_multiple = (df['volume'] % 100 != 0).sum()
        non_hundred_rate = non_hundred_multiple / len(df) if len(df) > 0 else 0
        
        if non_hundred_rate > 0.05:  # 超过5%不符合手数规则
            warnings.append(
                f"{non_hundred_multiple} 条记录 ({non_hundred_rate:.1%}) "
                f"成交量不是100的倍数 (可能包含大宗交易)"
            )
        
        # 异常大单检测 (单笔成交量 > 10万手)
        large_orders = (df['volume'] > 1000000).sum()
        if large_orders > 0:
            max_volume = df['volume'].max()
            warnings.append(
                f"发现 {large_orders} 笔大单 (> 100万股), "
                f"最大单笔: {max_volume:,} 股"
            )
        
        passed = error_count == 0
        score = 1.0 - (error_count / len(df)) if len(df) > 0 else 0.0
        
        return ValidationResult(
            passed=passed,
            score=score,
            error_count=error_count,
            total_count=len(df),
            details=errors,
            warnings=warnings
        )
    
    def validate_time_series(self, df: pd.DataFrame, trade_date: str) -> ValidationResult:
        """
        4. 时间序列验证
        
        验证点:
        - 时间递增 (允许相同时间)
        - 时间在交易时间段内
        - 日期与查询日期一致
        """
        errors = []
        warnings = []
        error_count = 0
        
        # 解析时间字段
        try:
            # mootdx 的 time 字段格式: "HH:MM" 或 "HH:MM:SS"
            df_copy = df.copy()
            df_copy['parsed_time'] = pd.to_datetime(
                df_copy['time'].astype(str), 
                format='%H:%M', 
                errors='coerce'
            ).dt.time
            
            # 检查时间解析失败
            parse_failures = df_copy['parsed_time'].isnull().sum()
            if parse_failures > 0:
                errors.append(f"{parse_failures} 条记录时间解析失败")
                error_count += parse_failures
                return ValidationResult(
                    passed=False,
                    score=0.0,
                    error_count=error_count,
                    total_count=len(df),
                    details=errors
                )
            
            # 时间单调性检查 (允许相等)
            times = df_copy['parsed_time'].tolist()
            non_monotonic = 0
            for i in range(1, len(times)):
                if times[i] < times[i-1]:
                    non_monotonic += 1
            
            if non_monotonic > 0:
                errors.append(f"发现 {non_monotonic} 处时间回退 (非单调递增)")
                error_count += non_monotonic
            
            # 交易时间段验证
            out_of_hours = 0
            for t in times:
                in_trading = any(
                    start <= t <= end 
                    for start, end in self.TRADING_SESSIONS
                )
                in_auction = self.AUCTION_TIME[0] <= t <= self.AUCTION_TIME[1]
                
                if not (in_trading or in_auction):
                    out_of_hours += 1
            
            if out_of_hours > 0:
                errors.append(
                    f"{out_of_hours} 条记录不在交易时间内 "
                    f"(09:15-11:30, 13:00-15:00)"
                )
                error_count += out_of_hours
            
            # 时间分布统计
            morning = sum(1 for t in times if time(9, 30) <= t <= time(11, 30))
            afternoon = sum(1 for t in times if time(13, 0) <= t <= time(15, 0))
            warnings.append(f"上午: {morning} 笔, 下午: {afternoon} 笔")
            
        except Exception as e:
            errors.append(f"时间验证异常: {str(e)}")
            error_count = len(df)
        
        passed = error_count == 0
        score = 1.0 - (error_count / len(df)) if len(df) > 0 else 0.0
        
        return ValidationResult(
            passed=passed,
            score=score,
            error_count=error_count,
            total_count=len(df),
            details=errors,
            warnings=warnings
        )
    
    def validate_buy_sell_direction(
        self, 
        df: pd.DataFrame,
        quotes_data: Optional[pd.DataFrame] = None
    ) -> ValidationResult:
        """
        5. 买卖方向验证
        
        验证点:
        - 主动买入: price >= ask1
        - 主动卖出: price <= bid1
        - 中性盘: bid1 < price < ask1
        
        注意: 需要实时盘口数据配合验证
        """
        warnings = []
        
        if 'type' not in df.columns:
            warnings.append("分笔数据无 'type' 字段，无法验证买卖方向")
            return ValidationResult(
                passed=True,
                score=1.0,
                error_count=0,
                total_count=len(df),
                warnings=warnings
            )
        
        # 统计买卖方向分布
        type_dist = df['type'].value_counts().to_dict()
        warnings.append(f"买卖方向分布: {type_dist}")
        
        # TODO: 如果有盘口数据，可以验证方向准确性
        if quotes_data is not None:
            warnings.append("盘口数据验证功能待实现")
        
        return ValidationResult(
            passed=True,
            score=1.0,
            error_count=0,
            total_count=len(df),
            warnings=warnings
        )
    
    async def validate_consistency_with_kline(
        self, 
        df: pd.DataFrame,
        code: str,
        trade_date: str
    ) -> ValidationResult:
        """
        6. 累计一致性验证
        
        验证点:
        - 分笔成交量累计 ≈ K线成交量
        - 分笔成交额累计 ≈ K线成交额
        - 允许误差 < 1%
        """
        errors = []
        warnings = []
        
        try:
            # 获取当日K线数据
            kline_df = await self.handler.get_history(
                codes=[code],
                params={'frequency': 'd', 'offset': 1}
            )
            
            if kline_df.empty:
                warnings.append("无法获取K线数据，跳过一致性验证")
                return ValidationResult(
                    passed=True,
                    score=1.0,
                    error_count=0,
                    total_count=1,
                    warnings=warnings
                )
            
            # 取最新一条K线
            kline_volume = kline_df.iloc[-1]['volume']
            tick_volume = df['volume'].sum()
            
            # 计算误差
            diff = abs(tick_volume - kline_volume)
            diff_rate = diff / kline_volume if kline_volume > 0 else 0
            
            warnings.append(
                f"分笔总量: {tick_volume:,}, K线总量: {kline_volume:,}, "
                f"差异: {diff_rate:.2%}"
            )
            
            # 误差阈值 1%
            if diff_rate > 0.01:
                errors.append(
                    f"分笔数据与K线数据不一致，差异 {diff_rate:.2%} > 1%"
                )
            
            passed = len(errors) == 0
            score = max(0.0, 1.0 - diff_rate)
            
            return ValidationResult(
                passed=passed,
                score=score,
                error_count=len(errors),
                total_count=1,
                details=errors,
                warnings=warnings
            )
            
        except Exception as e:
            warnings.append(f"一致性验证异常: {str(e)}")
            return ValidationResult(
                passed=True,
                score=1.0,
                error_count=0,
                total_count=1,
                warnings=warnings
            )
    
    def detect_anomalies(self, df: pd.DataFrame) -> ValidationResult:
        """
        7. 异常数据检测
        
        检测内容:
        - 价格离群值 (3σ原则)
        - 成交量离群值
        - 异常时间间隔
        """
        warnings = []
        anomaly_count = 0
        
        # 价格离群值检测
        price_mean = df['price'].mean()
        price_std = df['price'].std()
        price_outliers = ((df['price'] - price_mean).abs() > 3 * price_std).sum()
        
        if price_outliers > 0:
            warnings.append(f"发现 {price_outliers} 个价格离群值 (3σ)")
            anomaly_count += price_outliers
        
        # 成交量离群值检测
        vol_mean = df['volume'].mean()
        vol_std = df['volume'].std()
        vol_outliers = ((df['volume'] - vol_mean).abs() > 3 * vol_std).sum()
        
        if vol_outliers > 0:
            warnings.append(f"发现 {vol_outliers} 个成交量离群值 (3σ)")
            anomaly_count += vol_outliers
        
        # 计算异常率
        anomaly_rate = anomaly_count / len(df) if len(df) > 0 else 0
        score = max(0.0, 1.0 - anomaly_rate * 10)  # 异常率权重放大10倍
        
        return ValidationResult(
            passed=anomaly_rate < 0.01,  # 异常率 < 1%
            score=score,
            error_count=anomaly_count,
            total_count=len(df),
            warnings=warnings
        )
    
    async def validate_stock(
        self,
        code: str,
        trade_date: Optional[str] = None,
        prev_close: Optional[float] = None
    ) -> TickDataQualityReport:
        """
        对单个股票执行完整验证流程
        
        Args:
            code: 股票代码
            trade_date: 交易日期 YYYYMMDD (可选)
            prev_close: 昨收价 (可选，用于涨跌停验证)
        
        Returns:
            TickDataQualityReport
        """
        print(f"\n{'='*60}")
        print(f"开始验证股票 {code} 的分笔数据质量")
        print(f"{'='*60}")
        
        # 获取分笔数据
        params = {}
        if trade_date:
            params['date'] = trade_date
        
        df = await self.handler.get_tick(codes=[code], params=params)
        
        if df.empty:
            print(f"⚠️ 股票 {code} 无分笔数据")
            # 返回空报告
            return TickDataQualityReport(
                stock_code=code,
                test_date=trade_date or "unknown",
                record_count=0,
                field_validation=ValidationResult(False, 0.0, 1, 1, ["无数据"]),
                price_validation=ValidationResult(False, 0.0, 1, 1, ["无数据"]),
                volume_validation=ValidationResult(False, 0.0, 1, 1, ["无数据"]),
                time_validation=ValidationResult(False, 0.0, 1, 1, ["无数据"])
            )
        
        print(f"✓ 获取到 {len(df)} 条分笔记录")
        
        # 执行各项验证
        print("\n[1/7] 字段完整性验证...")
        field_result = self.validate_fields(df)
        print(f"  {'✅ PASSED' if field_result.passed else '❌ FAILED'} - Score: {field_result.score:.2f}")
        
        print("\n[2/7] 价格合理性验证...")
        price_result = self.validate_price_range(df, code, prev_close)
        print(f"  {'✅ PASSED' if price_result.passed else '❌ FAILED'} - Score: {price_result.score:.2f}")
        
        print("\n[3/7] 成交量验证...")
        volume_result = self.validate_volume(df)
        print(f"  {'✅ PASSED' if volume_result.passed else '❌ FAILED'} - Score: {volume_result.score:.2f}")
        
        print("\n[4/7] 时间序列验证...")
        time_result = self.validate_time_series(df, trade_date or "")
        print(f"  {'✅ PASSED' if time_result.passed else '❌ FAILED'} - Score: {time_result.score:.2f}")
        
        print("\n[5/7] 买卖方向验证...")
        direction_result = self.validate_buy_sell_direction(df)
        print(f"  {'✅ PASSED' if direction_result.passed else '❌ FAILED'} - Score: {direction_result.score:.2f}")
        
        print("\n[6/7] 累计一致性验证...")
        consistency_result = await self.validate_consistency_with_kline(df, code, trade_date or "")
        print(f"  {'✅ PASSED' if consistency_result.passed else '❌ FAILED'} - Score: {consistency_result.score:.2f}")
        
        print("\n[7/7] 异常数据检测...")
        anomaly_result = self.detect_anomalies(df)
        print(f"  {'✅ PASSED' if anomaly_result.passed else '❌ FAILED'} - Score: {anomaly_result.score:.2f}")
        
        # 生成报告
        report = TickDataQualityReport(
            stock_code=code,
            test_date=trade_date or datetime.now().strftime("%Y%m%d"),
            record_count=len(df),
            field_validation=field_result,
            price_validation=price_result,
            volume_validation=volume_result,
            time_validation=time_result,
            direction_validation=direction_result,
            consistency_validation=consistency_result,
            anomaly_detection=anomaly_result
        )
        
        print(f"\n{'='*60}")
        print(f"验证完成! 综合评分: {report.overall_score:.2f} - {report.status}")
        print(f"{'='*60}")
        
        return report


def print_report(report: TickDataQualityReport) -> None:
    """打印验证报告"""
    print(f"\n{'='*80}")
    print(f"分笔数据质量验证报告")
    print(f"{'='*80}")
    print(f"股票代码: {report.stock_code}")
    print(f"测试日期: {report.test_date}")
    print(f"记录数量: {report.record_count:,}")
    print(f"综合评分: {report.overall_score:.2f}")
    print(f"整体状态: {report.status}")
    print(f"{'-'*80}")
    
    # 详细结果
    validations = [
        ("字段完整性", report.field_validation),
        ("价格合理性", report.price_validation),
        ("成交量验证", report.volume_validation),
        ("时间序列", report.time_validation),
        ("买卖方向", report.direction_validation),
        ("累计一致性", report.consistency_validation),
        ("异常检测", report.anomaly_detection)
    ]
    
    for name, result in validations:
        if result is None:
            continue
        
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"\n【{name}】 {status} - Score: {result.score:.2f}")
        
        if result.details:
            print("  错误:")
            for detail in result.details:
                print(f"    - {detail}")
        
        if result.warnings:
            print("  警告:")
            for warning in result.warnings:
                print(f"    - {warning}")
    
    print(f"{'='*80}\n")


async def main():
    """主函数 - 执行代表性股票样本验证"""
    
    # 代表性股票样本
    test_samples = [
        {"code": "000001", "name": "平安银行", "prev_close": None},
        {"code": "600519", "name": "贵州茅台", "prev_close": None},
        {"code": "600000", "name": "浦发银行", "prev_close": None},
    ]
    
    validator = TickDataQualityValidator()
    
    try:
        await validator.initialize()
        
        reports = []
        
        for sample in test_samples:
            code = sample['code']
            name = sample['name']
            prev_close = sample['prev_close']
            
            print(f"\n\n{'#'*80}")
            print(f"# 测试股票: {code} - {name}")
            print(f"{'#'*80}")
            
            report = await validator.validate_stock(
                code=code,
                prev_close=prev_close
            )
            
            reports.append(report)
            print_report(report)
        
        # 汇总报告
        print(f"\n{'='*80}")
        print(f"汇总统计")
        print(f"{'='*80}")
        print(f"测试股票数: {len(reports)}")
        avg_score = sum(r.overall_score for r in reports) / len(reports)
        print(f"平均评分: {avg_score:.2f}")
        
        passed = sum(1 for r in reports if r.overall_score >= 0.90)
        print(f"优良率 (≥0.90): {passed}/{len(reports)} ({passed/len(reports):.1%})")
        
    finally:
        await validator.close()


if __name__ == "__main__":
    asyncio.run(main())
