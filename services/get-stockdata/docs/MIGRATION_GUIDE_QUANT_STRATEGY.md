# Quant-Strategy Migration Guide: Mock to Real Data

This guide outlines the steps to migrate the `quant-strategy` service from using local Mock data to consuming the new Real Data APIs provided by the `get-stockdata` service (EPIC-002 & EPIC-005).

## 1. Configuration Changes

Update your `.env` or configuration file to enable real data sources.

```env
# Enable real data source
DATA_SOURCE_TYPE=api
# Point to get-stockdata service
STOCK_DATA_SERVICE_URL=http://get-stockdata:8003/api/v1
```

## 2. API Mappings

Replace your mock data calls with the following API endpoints:

### 2.1 Financial Data (Fundamental Scoring)

| Data Point | Old Mock Source | New API Endpoint |
|------------|-----------------|------------------|
| Revenue, Profit | `mock_financials.json` | `GET /finance/indicators/{code}` |
| Historical Growth | `mock_history.json` | `GET /finance/history/{code}?periods=8` |
| PE/PB Ratios | `mock_valuation.json` | `GET /market/valuation/{code}` |
| Industry Stats | `mock_industry.json` | `GET /finance/industry/{code}/stats` |

**Example Response Mapping:**
```python
# Old Mock
financials = {
    "revenue": 1000,
    "net_profit": 200
}

# New API Response
response = client.get(f"/finance/indicators/{code}")
financials = {
    "revenue": response["revenue"],        # Unit: 亿元
    "net_profit": response["net_profit"]   # Unit: 亿元
}
```

### 2.2 Market Data (Swing Strategy)

| Data Point | Old Mock Source | New API Endpoint |
|------------|-----------------|------------------|
| Real-time Price | `mock_quotes.json` | `GET /quotes/realtime?codes={code}` |
| Liquidity (Vol) | `mock_liquidity.json`| `GET /stocks/{code}/liquidity` |
| Trading Status | `mock_status.json` | `GET /stocks/{code}/status` |

### 2.3 Stock Pool

| Data Point | Old Mock Source | New API Endpoint |
|------------|-----------------|------------------|
| Stock List | `mock_stock_list.json` | `GET /stocks/list` (Enhanced with caps) |

## 3. Data Units & Formats

> [!IMPORTANT]  
> **Unit Standardization**: The new APIs return monetary values in **亿元 (Billion CNY)** by default for financial statements/market cap to reduce integer overflow risks and align with industry standards.
> Mock data might have used raw Yuan. Please check your scoring formulas!

- **Revenue/Assets/MarketCap**: `float` (Unit: 10^8 CNY)
- **Ratios (PE/PB/ROE)**: `float` (e.g., `25.5` means 25.5%, or 25.5x)
- **Percentages**: APIs return absolute numbers (e.g., `15.5` for 15.5%), NOT decimals (`0.155`).

## 4. Error Handling

Real APIs may fail due to network issues or upstream data source limits.

- **404 Not Found**: Data unavailable for this specific stock/period. Treat as "N/A" or skip.
- **503 Service Unavailable**: Data service is initializing or upstream is down. Implement retry with backoff.
- **Timeouts**: Valuation APIs can take up to 2-3 seconds for cold cache. Set timeout > 5s.

## 5. Verification Checklist

- [ ] Verify `get_financials` calls return valid JSON.
- [ ] Check if `revenue` / `market_cap` scoring logic handles "亿元" unit correctly.
- [ ] Ensure `PE_TTM` is used instead of static PE where appropriate.
- [ ] Test graceful degradation if `get-stockdata` returns 503.
