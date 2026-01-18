from typing import List, Set
from gsd_shared.validation.standards import StockListStandards
from gsd_shared.validation.result import ValidationResult, ValidationIssue, ValidationLevel
from gsd_shared.validators import is_valid_a_stock

class StockListValidator:
    """股票名单校验器"""
    
    def validate_list_quality(self, stocks: List[str], date_str: str) -> ValidationResult:
        """校验全量名单质量"""
        result = ValidationResult("stock_list", date_str)
        count = len(stocks)
        
        # 数量校验
        if count < StockListStandards.MIN_COUNT:
            result.add_issue(ValidationIssue(
                "count", ValidationLevel.FAIL, f"Stock count {count} too low (< {StockListStandards.MIN_COUNT})"
            ))
        elif count > StockListStandards.MAX_COUNT:
             result.add_issue(ValidationIssue(
                "count", ValidationLevel.WARN, f"Stock count {count} unusually high (> {StockListStandards.MAX_COUNT})"
            ))
        
        # 格式校验 (抽样或全量)
        invalid_format_count = 0
        for code in stocks:
            if not is_valid_a_stock(code):
                invalid_format_count += 1
                
        if invalid_format_count > 0:
            result.add_issue(ValidationIssue(
                "format", 
                ValidationLevel.WARN if invalid_format_count < 10 else ValidationLevel.FAIL, 
                f"Found {invalid_format_count} invalid stock codes"
            ))
            
        return result

    def validate_incremental_change(self, current_set: Set[str], previous_set: Set[str], date_str: str) -> ValidationResult:
        """校验增量变化"""
        result = ValidationResult("stock_list", date_str)
        
        if not previous_set:
             return result 
             
        # 计算 Jaccard 相似度或重叠率
        intersection = len(current_set.intersection(previous_set))
        overlap_ratio = intersection / len(previous_set)
        
        if overlap_ratio < StockListStandards.MIN_OVERLAP_RATIO:
            result.add_issue(ValidationIssue(
                "stability", 
                ValidationLevel.WARN, 
                f"List overlap ratio {overlap_ratio:.2%} < threshold {StockListStandards.MIN_OVERLAP_RATIO:.0%}"
            ))
            
        return result
