import pytest
from gsd_shared.validation import (
    TickStandards, KLineStandards, StockListStandards,
    ValidationResult, ValidationIssue, ValidationLevel,
    TickValidator, KLineValidator, StockListValidator
)

class TestValidationStandards:
    def test_tick_standards_constants(self):
        # 宽松标准
        assert TickStandards.Loose.MIN_COUNT == 2000
        
        # 历史标准
        assert TickStandards.History.MIN_ACTIVE_MINUTES == 237
        assert TickStandards.History.PRICE_TOLERANCE == 0.011
        
        # 盘后当日标准
        assert TickStandards.IntradayPostMarket.MIN_ACTIVE_MINUTES == 230
        
    def test_kline_standards_constants(self):
        assert KLineStandards.MIN_COVERAGE_RATE == 98.0
        
    def test_stock_list_standards_constants(self):
        assert StockListStandards.MAX_COUNT == 6000

class TestValidationResult:
    def test_result_level_promotion(self):
        res = ValidationResult("test", "target")
        assert res.level == ValidationLevel.PASS
        assert res.is_passed()
        
        # Add WARN
        res.add_issue(ValidationIssue("d1", ValidationLevel.WARN, "warning"))
        assert res.level == ValidationLevel.WARN
        assert res.is_passed()
        
        # Add PASS (should remain WARN)
        res.add_issue(ValidationIssue("d2", ValidationLevel.PASS, "pass"))
        assert res.level == ValidationLevel.WARN
        
        # Add FAIL (should promote to FAIL)
        res.add_issue(ValidationIssue("d3", ValidationLevel.FAIL, "fail"))
        assert res.level == ValidationLevel.FAIL
        assert not res.is_passed()

class TestKLineValidator:
    def test_validate_daily_coverage(self):
        validator = KLineValidator()
        
        # Perfect case
        res = validator.validate_daily_coverage(100, 100, "2023-01-01")
        assert res.is_passed()
        
        # Warning case (not implemented in code, code only has FAIL if < 98%)
        # Let's test FAIL case
        res = validator.validate_daily_coverage(97, 100, "2023-01-01")
        assert not res.is_passed()
        assert res.issues[0].level == ValidationLevel.FAIL

    def test_validate_ohlc(self):
        validator = KLineValidator()
        
        # Valid
        res = validator.validate_ohlc(10.0, 11.0, 9.0, 10.5, "000001")
        assert res.is_passed()
        
        # Invalid: High < Low
        res = validator.validate_ohlc(10.0, 9.0, 11.0, 10.5, "000001")
        assert not res.is_passed()
        assert "High < Low" in res.issues[0].message

class TestStockListValidator:
    def test_validate_list_quality(self):
        validator = StockListValidator()
        
        # Too few
        res = validator.validate_list_quality(["000001"] * 100, "2023-01-01")
        assert not res.is_passed()
        assert "too low" in res.issues[0].message
        
        # Invalid format
        res = validator.validate_list_quality(["000001", "INVALID", "123"], "2023-01-01")
        # Count is low, so first issue is count.
        # Let's construct a list with valid count but invalid items
        stocks = ["000001"] * 5000 + ["INVALID"] * 20
        res = validator.validate_list_quality(stocks, "2023-01-01")
        # Should be FAIL because invalid count > 0 (logic says >0 is WARN/FAIL depending on count)
        # code: if invalid_format_count < 10 then WARN else FAIL
        # Here 20 invalid -> FAIL
        assert not res.is_passed()
        
