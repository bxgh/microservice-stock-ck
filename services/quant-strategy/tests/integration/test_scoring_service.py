import pytest
from services.alpha.fundamental_scoring_service import fundamental_scoring_service
from adapters.stock_data_provider import data_provider


@pytest.mark.asyncio
async def test_hybrid_scoring_workflow(mocker):
    """
    Test full scoring workflow with hybrid logic:
    Case A: Industry stats available -> Relative scoring
    Case B: Industry stats fail -> Fallback to absolute scoring
    """
    
    # Mock Financial Data (High-quality stock)
    from domain.models.financial_models import FinancialIndicators
    mock_fin = FinancialIndicators(
        stock_code="600519",
        roe=0.22,  # Excellent profitability
        revenue_growth_yoy=0.18,
        net_profit_growth_yoy=0.16,
        operating_cash_flow=120.0,
        net_profit=100.0
    )

    # Mock Industry Stats (For Relative Mode)
    mock_industry_stats = {
        'industry_code': '酿酒行业',
        'industry_name': '酿酒行业',
        'stock_count': 50,
        'roe_stats': {
            'mean': 0.12,
            'median': 0.10,
            'p25': 0.08,
            'p50': 0.10,
            'p75': 0.15,
            'p90': 0.20,
            'min': 0.02,
            'max': 0.30
        },
        'revenue_growth_stats': {
            'mean': 0.10,
            'median': 0.08,
            'p25': 0.05,
            'p50': 0.08,
            'p75': 0.12,
            'min': -0.05,
            'max': 0.25
        }
    }

    # Case A: With Industry Stats (Relative Scoring)
    mocker.patch.object(data_provider, 'get_financial_indicators', return_value=mock_fin)
    mocker.patch.object(data_provider, 'get_industry_stats', return_value=mock_industry_stats)

    score_a = await fundamental_scoring_service.score_stock("600519", industry_code="酿酒行业")
    
    assert score_a is not None
    assert score_a.scoring_mode.value == "relative"
    assert score_a.total_score > 80  # High-quality stock should score high
    assert score_a.profitability.mode.value == "relative"
    
    # Case B: Without Industry Stats (Absolute Fallback)
    mocker.patch.object(data_provider, 'get_industry_stats', return_value=None)

    score_b = await fundamental_scoring_service.score_stock("600519", industry_code="酿酒行业")
    
    assert score_b is not None
    assert score_b.scoring_mode.value == "absolute"
    assert score_b.total_score > 80  # Should still score high via absolute thresholds


@pytest.mark.asyncio
async def test_low_quality_stock_scoring(mocker):
    """Verify that low-quality stocks receive appropriately low scores"""
    
    from domain.models.financial_models import FinancialIndicators
    
    # Mock Financial Data (Low-quality stock)
    mock_fin_poor = FinancialIndicators(
        stock_code="POOR",
        roe=0.03,  # Poor profitability
        revenue_growth_yoy=-0.05,  # Negative growth
        net_profit_growth_yoy=-0.10,
        operating_cash_flow=30.0,
        net_profit=100.0
    )

    mocker.patch.object(data_provider, 'get_financial_indicators', return_value=mock_fin_poor)
    mocker.patch.object(data_provider, 'get_industry_stats', return_value=None)

    score = await fundamental_scoring_service.score_stock("POOR")
    
    assert score is not None
    assert score.total_score < 50  # Low-quality stock should score low
    assert score.profitability.weighted_score <= 60
    assert score.growth.weighted_score <= 40
