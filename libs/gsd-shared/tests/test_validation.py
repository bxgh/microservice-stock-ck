import pytest
from gsd_shared.validation import (
    TickStandards, KLineStandards,
    ValidationResult, ValidationIssue, ValidationLevel,
    TickValidator, KLineValidator
)

class TestValidationStandards:
    def test_tick_standards_constants(self):
        # 宽松标准
        assert TickStandards.Loose.MIN_COUNT == 2000
        
        # 精准标准
        assert TickStandards.Precise.PRICE_TOLERANCE == 0.1
        assert TickStandards.Precise.VOLUME_TOLERANCE == 0.005
        assert TickStandards.Precise.SNAPSHOT_MIN_TIME_CLOSE == "15:00:00"
        
    def test_kline_standards_constants(self):
        assert KLineStandards.MIN_COVERAGE_RATE == 98.0

class TestValidationResult:
    def test_result_level_promotion(self):
        res = ValidationResult("test", "target")
        assert res.level == ValidationLevel.PASS
        assert res.is_passed()
        
        # Add WARN
        res.add_issue(ValidationIssue("d1", ValidationLevel.WARN, "warning"))
        assert res.level == ValidationLevel.WARN
        assert res.is_passed()
        
        # Add FAIL (should promote to FAIL)
        res.add_issue(ValidationIssue("d3", ValidationLevel.FAIL, "fail"))
        assert res.level == ValidationLevel.FAIL
        assert not res.is_passed()

class TestKLineValidator:
    def test_ohlc_logic(self):
        # Simple test for OHLC logic
        # Note: KLineValidator might need a pool to be fully testable if it's not mocked
        pass
