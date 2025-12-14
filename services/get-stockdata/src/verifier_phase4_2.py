
import asyncio
import logging
from src.data_services.quotes_service import QuotesService
from src.models.stock_models import StockInfo, StockCodeMapping

async def verify_list_enrichment():
    print("--- Verifying EPIC-005 Phase 4.2: Stock List Enrichment ---")
    
    # 1. Init Quotes Service
    quotes_service = QuotesService(enable_cache=True)
    await quotes_service.initialize()
    
    # 2. Mock Stock Data (as if from StockCodeClient)
    print("Mocking Stock List...")
    # Create valid StockInfo objects
    mock_stocks = [
        StockInfo(
            stock_code="600519", 
            stock_name="贵州茅台", 
            exchange="SH", 
            code_mappings=StockCodeMapping(
                standard="600519", tushare="600519.SH", akshare="600519",
                tonghua_shun="600519", wind="600519.SH", east_money="600519"
            ),
            is_active=True
        ),
        StockInfo(
            stock_code="000001", 
            stock_name="平安银行", 
            exchange="SZ", 
            code_mappings=StockCodeMapping(
                 standard="000001", tushare="000001.SZ", akshare="000001",
                 tonghua_shun="000001", wind="000001.SZ", east_money="000001"
            ),
            is_active=True
        )
    ]
    
    # 3. Enrich Logic (Simulating route logic)
    print("Enriching...")
    try:
        codes = [s.stock_code for s in mock_stocks]
        quotes = await quotes_service.get_realtime_quotes(codes)
        quote_map = {q['code']: q for q in quotes}
        
        for stock in mock_stocks:
            if stock.stock_code in quote_map:
                q = quote_map[stock.stock_code]
                if q.get('market_cap'):
                    stock.market_cap = q.get('market_cap') / 100000000.0
                    print(f" -> {stock.stock_name}: Market Cap set to {stock.market_cap:.2f} 亿元")
                
                if q.get('turnover_ratio'):
                    stock.turnover_ratio = q.get('turnover_ratio')
                    print(f" -> {stock.stock_name}: Turnover Ratio set to {stock.turnover_ratio}%")
            else:
                print(f" -> {stock.stock_name}: No quote found")

        # Assertion
        print(f"Verification Check: {mock_stocks[0].market_cap} for {mock_stocks[0].stock_name}")
        assert any(s.market_cap is not None for s in mock_stocks), "Market Cap not set"
        print("✅ Verification Success")

    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        
    await quotes_service._cache_manager.close()

if __name__ == "__main__":
    asyncio.run(verify_list_enrichment())
