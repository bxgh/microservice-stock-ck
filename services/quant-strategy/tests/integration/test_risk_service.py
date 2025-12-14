import pytest
from services.alpha.risk_service import risk_service
from adapters.stock_data_provider import data_provider

# Mock provider response for integration test simulation
# In a real integration test, we might mock the HTTP calls or use a test env.
# here we rely on the provider's 'mock' mode if implemented, or we mock the provider method.

@pytest.mark.asyncio
async def test_risk_service_flow(mocker):
    """
    Verify Risk Service correctly orchestrates data fetching and rule checking.
    """
    
    # 1. Mock Data Provider returns
    # Stock A: Healthy
    mock_info_a = {'listing_status': 'L', 'market_cap': 100.0, 'amount': 50000000.0}
    mock_fin_a = mocker.Mock()
    mock_fin_a.dict.return_value = {
        'goodwill': 0, 'net_assets': 100,
        'major_shareholder_pledge_ratio': 0.1,
        'net_profit': 10, 'operating_cash_flow': 10,
        'monetary_funds': 10, 'interest_bearing_debt': 10, 'total_assets': 100
    }
    
    # Stock B: ST
    mock_info_b = {'listing_status': 'L', 'is_st': True}
    mock_fin_b = mocker.Mock()
    mock_fin_b.dict.return_value = {}
    
    # Stock C: Goodwill Bomb
    mock_info_c = {'listing_status': 'L', 'market_cap': 100.0, 'amount': 50000000.0}
    mock_fin_c = mocker.Mock()
    mock_fin_c.dict.return_value = {
        'goodwill': 50, 'net_assets': 100, # 50% ratio > 30%
        'major_shareholder_pledge_ratio': 0.1,
        'net_profit': 10, 'operating_cash_flow': 10,
        'monetary_funds': 10, 'interest_bearing_debt': 10, 'total_assets': 100
    }

    async def get_info_side_effect(code):
        if code == 'A': return mock_info_a
        if code == 'B': return mock_info_b
        if code == 'C': return mock_info_c
        return {}

    async def get_fin_side_effect(code):
        if code == 'A': return mock_fin_a
        if code == 'B': return mock_fin_b
        if code == 'C': return mock_fin_c # Should be object but dict for fail check in merge
        # Fix mock for C to be object that has .dict()
        return mock_fin_c

    mocker.patch.object(data_provider, 'get_stock_info', side_effect=get_info_side_effect)
    mocker.patch.object(data_provider, 'get_financial_indicators', side_effect=get_fin_side_effect)

    # 2. Run Checks
    results = await risk_service.check_stocks(['A', 'B', 'C'])
    
    # 3. Assess Results
    
    # Stock A -> Pass
    res_a = next(r for r in results if r.stock_code == 'A')
    assert not res_a.is_vetoed
    
    # Stock B -> Fail (Status)
    res_b = next(r for r in results if r.stock_code == 'B')
    assert res_b.is_vetoed
    assert any("Status" in r for r in res_b.veto_reasons)
    
    # Stock C -> Fail (Goodwill)
    res_c = next(r for r in results if r.stock_code == 'C')
    assert res_c.is_vetoed
    assert any("Goodwill" in r for r in res_c.veto_reasons)
