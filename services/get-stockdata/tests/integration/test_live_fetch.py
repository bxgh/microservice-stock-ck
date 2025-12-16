import httpx, os, pytest

BASE_URL = os.getenv("GET_STOCKDATA_URL", "http://127.0.0.1:8000")

@pytest.mark.integration
def test_live_stock_list():
    resp = httpx.get(f"{BASE_URL}/api/v1/stocks/list?limit=5")
    assert resp.status_code == 200, f"Unexpected status {resp.status_code}"
    data = resp.json()
    assert data.get("success") is True
    assert isinstance(data.get("data"), list) and len(data["data"]) > 0

@pytest.mark.integration
def test_live_valuation():
    # Example stock code – adjust if needed
    resp = httpx.get(f"{BASE_URL}/api/v1/valuation/history/600519")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("success") is True
