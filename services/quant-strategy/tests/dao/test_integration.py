import pytest
import pandas as pd
from dao.client import data_client
from dao.stock_info import StockInfoDAO
from dao.industry import IndustryDAO
from dao.kline import KLineDAO

# Integration tests requiring running mootdx-source
@pytest.mark.asyncio
async def test_stock_info_dao():
    dao = StockInfoDAO()
    
    # 1. Test get_stock_list
    codes = await dao.get_stock_list()
    print(f"Total stocks: {len(codes)}")
    assert isinstance(codes, list)
    # assert len(codes) > 0  # Depends on DB content
    
    # 2. Test get_stock_meta
    test_code = "600519" # Kweichow Moutai
    df_meta = await dao.get_stock_meta([test_code])
    print(f"Meta for {test_code}: {df_meta}")
    assert isinstance(df_meta, pd.DataFrame)
    if not df_meta.empty:
        assert 'code' in df_meta.columns
        assert df_meta.iloc[0]['code'] == test_code
        
    # 3. Test get_issue_price (NEW FEATURE)
    df_issue = await dao.get_issue_price([test_code])
    print(f"Issue Price for {test_code}: {df_issue}")
    assert isinstance(df_issue, pd.DataFrame)
    # If DB has data, check columns
    if not df_issue.empty:
        assert 'issue_price' in df_issue.columns

@pytest.mark.asyncio
async def test_industry_dao():
    dao = IndustryDAO()
    test_code = "600519"
    
    # Test get_sw_industry (NEW FEATURE)
    df_ind = await dao.get_sw_industry([test_code], level=3)
    print(f"Industry for {test_code}: {df_ind}")
    assert isinstance(df_ind, pd.DataFrame)
    if not df_ind.empty:
        assert 'industry_name' in df_ind.columns

@pytest.mark.asyncio
async def test_kline_dao():
    dao = KLineDAO()
    test_code = "600519"
    
    # Test get_kline
    df_kline = await dao.get_kline(
        [test_code], 
        start_date="2023-01-01", 
        end_date="2023-01-10"
    )
    print(f"KLine for {test_code}: {len(df_kline)} rows")
    assert isinstance(df_kline, pd.DataFrame)
    if not df_kline.empty:
        assert 'open' in df_kline.columns
        assert 'close' in df_kline.columns


