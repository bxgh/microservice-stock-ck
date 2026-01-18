from typing import Dict, Any, List
from gsd_shared.validation.standards import MarketStandards
from gsd_shared.validation.result import ValidationResult, ValidationIssue, ValidationLevel

class MarketValidator:
    """全市场级别校验器"""
    
    def validate_coverage(self, kline_count: int, stock_count: int, date_str: str) -> ValidationResult:
        """校验市场K线覆盖率"""
        result = ValidationResult("market", f"{date_str}_coverage")
        
        if stock_count == 0:
            result.add_issue(ValidationIssue("coverage", ValidationLevel.WARN, "Stock count is 0, skipping coverage check"))
            return result
            
        rate = (kline_count / stock_count) * 100
        
        if rate < MarketStandards.MIN_KLINE_COVERAGE_RATE:
            result.add_issue(ValidationIssue(
                "kline_coverage", 
                ValidationLevel.FAIL, 
                f"Market KLine coverage {rate:.2f}% < {MarketStandards.MIN_KLINE_COVERAGE_RATE}% ({kline_count}/{stock_count})"
            ))
        else:
            result.add_issue(ValidationIssue(
                "kline_coverage", ValidationLevel.PASS, f"Market KLine coverage: {rate:.2f}%"
            ))
            
        return result

    def validate_tick_coverage(self, tick_stock_count: int, kline_stock_count: int, date_str: str) -> ValidationResult:
        """校验市场Tick覆盖率 (相对于当日有交易的K线股票)"""
        result = ValidationResult("market", f"{date_str}_tick_coverage")
        
        if kline_stock_count == 0:
             return result

        rate = (tick_stock_count / kline_stock_count) * 100
        
        if rate < MarketStandards.MIN_TICK_COVERAGE_RATE:
            result.add_issue(ValidationIssue(
                "tick_coverage",
                ValidationLevel.FAIL,
                f"Market Tick coverage {rate:.2f}% < {MarketStandards.MIN_TICK_COVERAGE_RATE}% ({tick_stock_count}/{kline_stock_count})"
            ))
        else:
            result.add_issue(ValidationIssue(
                "tick_coverage", ValidationLevel.PASS, f"Market Tick coverage: {rate:.2f}%"
            ))
            
        return result

    def validate_market_continuity(self, abnormal_count: int, total_checked: int, date_str: str) -> ValidationResult:
        """校验市场整体连续性 (异常股票数量)"""
        result = ValidationResult("market", f"{date_str}_continuity")
        
        if abnormal_count > MarketStandards.MAX_ABNORMAL_STOCKS:
            result.add_issue(ValidationIssue(
                "continuity",
                ValidationLevel.FAIL,
                f"Too many abnormal stocks: {abnormal_count} > {MarketStandards.MAX_ABNORMAL_STOCKS}"
            ))
        elif abnormal_count > 0:
             result.add_issue(ValidationIssue(
                "continuity",
                ValidationLevel.WARN,
                f"Abnormal stocks detected: {abnormal_count}"
            ))
        else:
             result.add_issue(ValidationIssue(
                "continuity", ValidationLevel.PASS, "No abnormal stocks detected"
            ))
            
        return result
