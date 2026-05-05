import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch

from database.stock_pool_models import UniverseStock
from services.stock_pool.candidate_service import CandidatePoolService

@pytest.fixture
def candidate_service():
    """Provides a mocked CandidatePoolService instance"""
    provider_mock = AsyncMock()
    provider_mock.get_financial_indicators.return_value = {}
    provider_mock.get_valuation.return_value = {}
    provider_mock.get_industry_stats.return_value = {}
    # default to 60 to pass min_score_threshold=60.0
    fund_scoring_mock = AsyncMock()
    fund_result_mock = MagicMock()
    fund_result_mock.total_score = 60.0 
    fund_scoring_mock.score_stock.return_value = fund_result_mock
    
    val_service_mock = AsyncMock()
    val_result_mock = MagicMock()
    val_result_mock.total_score = 60.0
    val_service_mock.score_stock.return_value = val_result_mock

    service = CandidatePoolService(
        data_provider=provider_mock,
        fundamental_scoring=fund_scoring_mock,
        valuation_service=val_service_mock
    )
    return service

@pytest.mark.asyncio
async def test_eco_signal_bonus_injection(candidate_service):
    """
    Test that ecosystem signals ('HOT', 'WARM') are injected into the 
    candidate pool scores correctly.
    """
    # 1. Setup mocked universe stocks
    mock_universe = [
        UniverseStock(code="000001.SZ", industry="bank", is_qualified=True), # Base stock 
        UniverseStock(code="600000.SH", industry="ai", is_qualified=True),   # Expected to get bonus
    ]

    # 2. Setup mock data for Eco Signal DAO and Industry Concept DAO
    mock_signals_df = pd.DataFrame([{
        "label": "deepseek",
        "composite_z_score": 1.6,
        "dominant_factor": "eco_momentum",
        "signal_level": "HOT",
        "detail": "{}"
    }])

    mock_concepts_df = pd.DataFrame([
        {"ts_code": "600000.SH", "sector_name": "人工智能", "sector_type": "THS"}
    ])

    with patch('services.stock_pool.candidate_service.get_session') as mock_get_session:
        # Mock database session
        mock_session = AsyncMock()
        # Mock universe stock select
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_universe
        mock_session.execute.return_value = mock_result
        
        # Make get_session an async generator
        async def _get_session():
            yield mock_session
        mock_get_session.side_effect = _get_session

        # 3. Patch _get_eco_bonuses on the service instance
        # 600000.SH gets a 10.0 bonus for HOT deepseek
        with patch.object(candidate_service, '_get_eco_bonuses', new_callable=AsyncMock) as mock_get_eco_bonuses:
            mock_get_eco_bonuses.return_value = {
                "600000.SH": (10.0, "Eco[deepseek(HOT)->人工智能]")
            }

            # 4. Execute refresh_pool
            await candidate_service.refresh_pool(pool_type='long')

            # 5. Assertions
            # Check added candidate entries
            added_entries = mock_session.add_all.call_args[0][0]
            assert len(added_entries) == 2

            print("\nDEBUG:")
            for e in added_entries:
                print(f"Code: {e.code}, Score: {e.score}, Reason: {e.entry_reason}")

            # 000001.SZ gets base score (60.0 * 0.6 + 60.0 * 0.4 = 60.0)
            # 600000.SH gets base score + HOT bonus (60.0 + 10.0 = 70.0)
            # Therefore, 600000.SH should be ranked higher
            assert added_entries[0].code == "600000.SH"
            assert added_entries[0].score == 70.0
            assert "Eco[deepseek(HOT)->人工智能] (+10.0)" in added_entries[0].entry_reason
            
            assert added_entries[1].code == "000001.SZ"
            assert added_entries[1].score == 60.0
            assert "Eco" not in added_entries[1].entry_reason
