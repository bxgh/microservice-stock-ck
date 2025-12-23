
import asyncio
import logging
import sys
import os

# PYTHONPATH includes /app/src in the container
from adapters.stock_data_provider import data_provider
from services.alpha.fundamental_scoring_service import fundamental_scoring_service
from services.alpha.valuation_service import valuation_service
from services.stock_pool.candidate_service import CandidatePoolService
from database.stock_pool_models import UniverseStock
from database.session import get_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_scoring():
    print("Initializing data provider...")
    await data_provider.initialize()
    
    fundamental_scoring_service.data_provider = data_provider
    valuation_service.data_provider = data_provider
    
    candidate_service = CandidatePoolService(
        data_provider=data_provider,
        fundamental_scoring=fundamental_scoring_service,
        valuation_service=valuation_service
    )
    
    test_code = '000001' # Ping An Bank
    print(f"Testing real score for {test_code}...")
    
    print("Diving into individual services...")
    
    try:
        print(f"Fetching financial indicators for {test_code}...")
        financial_data = await data_provider.get_financial_indicators(test_code)
        print(f"Financial Data keys: {financial_data.__dict__.keys() if financial_data else 'None'}")
        
        print(f"Fetching valuation for {test_code}...")
        valuation_data = await data_provider.get_valuation(test_code)
        print(f"Valuation Data keys: {valuation_data.keys() if valuation_data else 'None'}")
        
        print(f"Fetching valuation history for {test_code}...")
        history_data = await data_provider.get_valuation_history(test_code, years=1)
        print(f"History Data keys: {history_data.keys() if history_data else 'None'}")
        
        print("Calculating fundamental score...")
        fund_result = await fundamental_scoring_service.score_stock(
            code=test_code,
            financials=financial_data,
            industry_stats=None,
            mode='absolute'
        )
        print(f"Fundamental Result Score: {fund_result.total_score if fund_result else 'None'}")
        
        print("Calculating valuation score...")
        val_result = await valuation_service.score_stock(
            code=test_code,
            current_valuation=valuation_data
        )
        print(f"Valuation Result Score: {val_result.total_score if val_result else 'None'}")

    except Exception as e:
        print(f"Caught Exception: {repr(e)}")
        import traceback
        traceback.print_exc()

    await data_provider.close()

    await data_provider.close()

if __name__ == "__main__":
    asyncio.run(test_scoring())
