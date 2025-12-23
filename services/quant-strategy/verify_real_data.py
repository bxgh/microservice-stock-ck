
import asyncio
import sys
import os
import json
from datetime import datetime, timedelta

# Ensure src is in python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from adapters.stock_data_provider import data_provider
from config.settings import settings

async def main():
    print(f"--- Configuration ---")
    print(f"Service URL: {settings.stockdata_service_url}")
    print(f"---------------------")

    # Initialize data provider
    await data_provider.initialize()

    test_stock = '600519' # Moutai
    test_codes = ['600519', '000001']

    print(f"\n[TestCase 1] Real-time Quotes for {test_codes}")
    try:
        df = await data_provider.get_realtime_quotes(test_codes)
        if not df.empty:
            print(f"SUCCESS: Fetched {len(df)} records.")
            print(df[['code', 'name', 'price', 'change_pct', 'timestamp']].head())
        else:
            print("WARNING: Returned empty DataFrame.")
    except Exception as e:
        print(f"ERROR: {e}")

    print(f"\n[TestCase 2] Stock List (Limit 5)")
    try:
        stocks = await data_provider.get_all_stocks(limit=5)
        if stocks:
            print(f"SUCCESS: Fetched {len(stocks)} stocks.")
            for s in stocks[:5]:
                print(f" - {s.get('code')} {s.get('name')} ({s.get('exchange')})")
        else:
             print("WARNING: Returned empty list.")
    except Exception as e:
        print(f"ERROR: {e}")

    print(f"\n[TestCase 3] Historical K-Line for {test_stock}")
    try:
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        df = await data_provider.get_history_bar(test_stock, start_date=start_date)
        if not df.empty:
            print(f"SUCCESS: Fetched {len(df)} bars.")
            print(df.head())
        else:
            print("WARNING: Returned empty DataFrame.")
    except Exception as e:
        print(f"ERROR: {e}")

    print(f"\n[TestCase 4] Tick Data for {test_stock}")
    try:
        df = await data_provider.get_tick_data(test_stock)
        if not df.empty:
            print(f"SUCCESS: Fetched {len(df)} ticks.")
            print(df.head())
        else:
            print("WARNING: Returned empty DataFrame (Market might be closed).")
    except Exception as e:
        print(f"ERROR: {e}")

    print(f"\n[TestCase 5] Market Ranking (limit_up)")
    try:
        df = await data_provider.get_market_ranking("limit_up")
        if not df.empty:
            print(f"SUCCESS: Fetched {len(df)} ranking items.")
            print(df.head())
        else:
            print("WARNING: Returned empty DataFrame.")
    except Exception as e:
        print(f"ERROR: {e}")

    print(f"\n[TestCase 6] Sector List")
    try:
        sectors = await data_provider.get_sector_list()
        if sectors:
            print(f"SUCCESS: Fetched {len(sectors)} sectors.")
            print(f"First sector: {sectors[0]}")
        else:
            print("WARNING: Returned empty sector list.")
    except Exception as e:
        print(f"ERROR: {e}")

    print(f"\n[TestCase 7] Capital Flow for {test_stock}")
    try:
        flow = await data_provider.get_capital_flow(test_stock)
        if flow:
            print(f"SUCCESS: Capital flow fetched.")
            print(json.dumps(flow, indent=2, ensure_ascii=False))
        else:
            print("WARNING: Returned empty capital flow.")
    except Exception as e:
        print(f"ERROR: {e}")

    print(f"\n[TestCase 8] Financial Indicators for {test_stock}")
    try:
        indicators = await data_provider.get_financial_indicators(test_stock)
        if indicators:
            print(f"SUCCESS: Financial indicators fetched.")
            # print(f"ROE: {indicators.roe}, Net Profit Margin: {indicators.net_profit_margin}")
        else:
            print("WARNING: Returned None.")
    except Exception as e:
        print(f"ERROR: {e}")

    print(f"\n[TestCase 9] Valuation for {test_stock}")
    try:
        valuation = await data_provider.get_valuation(test_stock)
        if valuation:
            print(f"SUCCESS: Valuation fetched.")
            print(json.dumps(valuation, indent=2, ensure_ascii=False))
        else:
            print("WARNING: Returned None.")
    except Exception as e:
        print(f"ERROR: {e}")

    print(f"\n[TestCase 10] Stock Info for {test_stock}")
    try:
        info = await data_provider.get_stock_info(test_stock)
        if info:
            print(f"SUCCESS: Stock info fetched.")
            print(json.dumps(info, indent=2, ensure_ascii=False))
        else:
            print("WARNING: Returned None.")
    except Exception as e:
        print(f"ERROR: {e}")

    await data_provider.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
