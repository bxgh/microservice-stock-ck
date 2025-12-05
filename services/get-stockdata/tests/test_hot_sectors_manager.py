"""
Test HotSectorsManager
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
import pandas as pd
from services.stock_pool.hot_sectors_manager import HotSectorsManager

@pytest.fixture
def mock_config_manager():
    manager = MagicMock()
    manager.get_config.return_value = {
        "hot_sectors": {
            "sectors": {
                "tech": {
                    "name": "Tech",
                    "size": 5,
                    "sources": [
                        {"type": "etf", "code": "512760", "top_n": 3}
                    ]
                },
                "manual_sector": {
                    "name": "Manual",
                    "size": 5,
                    "sources": [
                        {"type": "manual", "codes": ["600000", "600001"]}
                    ]
                }
            }
        }
    }
    return manager

@pytest.mark.asyncio
async def test_build_pool_aggregation(mock_config_manager, tmp_path):
    """测试池构建和聚合"""
    manager = HotSectorsManager(mock_config_manager, cache_dir=str(tmp_path))
    
    # Mock akshare
    with patch("services.stock_pool.hot_sectors_manager.ak") as mock_ak:
        # Mock ETF data
        mock_df = pd.DataFrame({
            "股票代码": ["000001", "000002", "000003"],
            "持仓占比": [10.0, 5.0, 3.0]
        })
        mock_ak.fund_etf_fund_info_em.return_value = mock_df
        
        pool = await manager.get_pool()
        
        # 3 from ETF + 2 from Manual = 5
        assert len(pool) == 5
        assert "000001" in pool
        assert "600000" in pool

@pytest.mark.asyncio
async def test_get_etf_stocks_fallback(mock_config_manager, tmp_path):
    """测试ETF获取降级方案"""
    manager = HotSectorsManager(mock_config_manager, cache_dir=str(tmp_path))
    
    with patch("services.stock_pool.hot_sectors_manager.ak") as mock_ak:
        # Primary method fails
        mock_ak.fund_etf_fund_info_em.side_effect = Exception("API Error")
        
        # Fallback method succeeds
        mock_fallback_df = pd.DataFrame({
            "品种代码": ["000001", "000002"]
        })
        mock_ak.index_stock_cons.return_value = mock_fallback_df
        
        # Call private method directly for testing
        stocks = await asyncio.to_thread(manager._get_etf_stocks_sync, "512760", 5)
        
        assert len(stocks) == 2
        assert "000001" in stocks

@pytest.mark.asyncio
async def test_monster_stocks(mock_config_manager, tmp_path):
    """测试妖股筛选"""
    manager = HotSectorsManager(mock_config_manager, cache_dir=str(tmp_path))
    
    config = {
        "size": 2,
        "criteria": [
            {"field": "涨跌幅", "operator": ">", "value": 5.0}
        ]
    }
    
    with patch("services.stock_pool.hot_sectors_manager.ak") as mock_ak:
        # Mock market data
        mock_df = pd.DataFrame({
            "代码": ["000001", "000002", "000003"],
            "涨跌幅": [10.0, 6.0, 2.0]
        })
        mock_ak.stock_zh_a_spot_em.return_value = mock_df
        
        stocks = await manager._get_monster_stocks(config)
        
        assert len(stocks) == 2
        assert "000001" in stocks # 10%
        assert "000002" in stocks # 6%
        assert "000003" not in stocks # 2% < 5%

@pytest.mark.asyncio
async def test_caching(mock_config_manager, tmp_path):
    """测试缓存机制"""
    manager = HotSectorsManager(mock_config_manager, cache_dir=str(tmp_path))
    
    # 1. First call builds pool
    with patch("services.stock_pool.hot_sectors_manager.ak") as mock_ak:
        mock_df = pd.DataFrame({"股票代码": ["000001"], "持仓占比": [10.0]})
        mock_ak.fund_etf_fund_info_em.return_value = mock_df
        
        await manager.get_pool()
        assert mock_ak.fund_etf_fund_info_em.called
        
    # 2. Second call uses cache (mock ak to raise error to prove it's not called)
    with patch("services.stock_pool.hot_sectors_manager.ak") as mock_ak:
        mock_ak.fund_etf_fund_info_em.side_effect = Exception("Should not be called")
        
        pool = await manager.get_pool()
        assert len(pool) == 3 # 1 from ETF + 2 from Manual
        assert "000001" in pool
