import pytest
from services.alpha.valuation_service import ValuationService
from adapters.stock_data_provider import data_provider
from domain.alpha.valuation_models import ValuationScore


class TestValuationLogic:
    """Test PE/PB Band Scoring Logic"""

    def setup_method(self):
        self.service = ValuationService()

    def test_calculate_band_score_undervalued(self):
        """Test < 25th percentile (Undervalued)"""
        # Range: 10 - 60, Current: 15 (Percentile = 10%)
        stats = {'min': 10, 'max': 60, 'median': 35}
        current = 15.0
        
        score = self.service._calculate_band_score("PE", current, stats)
        
        assert score.percentile == 10.0
        assert score.band_score == 100.0  # < 25%

    def test_calculate_band_score_fair(self):
        """Test 25-75th percentile (Fair)"""
        # Range: 10 - 60, Current: 35 (Percentile = 50%)
        stats = {'min': 10, 'max': 60, 'median': 35}
        current = 35.0
        
        score = self.service._calculate_band_score("PE", current, stats)
        
        assert score.percentile == 50.0
        assert score.band_score == 60.0  # 50-75% bracket starts at 50%? 
        # Check logic: < 50% => 80 pts. wait. 
        # Logic: 
        # < 25% -> 100
        # < 50% -> 80
        # < 75% -> 60
        # So exactly 50% is < 75% -> 60. Correct.

    def test_calculate_band_score_overvalued(self):
        """Test > 90th percentile (Bubble)"""
        # Range: 10 - 60, Current: 58 (Percentile = 96%)
        stats = {'min': 10, 'max': 60, 'median': 35}
        current = 58.0
        
        score = self.service._calculate_band_score("PE", current, stats)
        
        assert score.percentile == 96.0
        assert score.band_score == 20.0  # > 90%

    def test_invalid_data_protection(self):
        """Test protection against invalid ranges"""
        stats = {'min': 10, 'max': 10} # Zero range
        score = self.service._calculate_band_score("PE", 10, stats)
        assert score is None


@pytest.mark.asyncio
async def test_full_valuation_workflow(mocker):
    """Test complete valuation workflow with mocked data"""
    from services.alpha.valuation_service import valuation_service
    
    # Mock Current Data
    mocker.patch.object(data_provider, 'get_valuation', return_value={
        'pe_ttm': 20.0,
        'pb_ratio': 5.0
    })
    
    # Mock History Data
    mocker.patch.object(data_provider, 'get_valuation_history', return_value={
        'stats': {
            'pe_ttm': {'min': 10, 'max': 60, 'median': 30},  # PE=20 -> P20 (Cheap)
            'pb_ratio': {'min': 2, 'max': 10, 'median': 6}    # PB=5 -> P37.5 (Fair)
        }
    })

    score = await valuation_service.score_stock_valuation("TEST")
    
    assert score is not None
    # PE Score: P20 < P25 => 100 pts
    assert score.pe_score.band_score == 100.0
    
    # PB Score: P37.5 < P50 => 80 pts (Fair Low)
    assert score.pb_score.band_score == 80.0
    
    # Total: (100 + 80) / 2 = 90
    assert score.total_score == 90.0
    assert score.valuation_status == "Undervalued"
