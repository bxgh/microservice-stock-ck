"""
Universe Pool Integration Tests

按照编程规范要求:
1. 使用真实数据 (禁止 Mock)
2. 在 Docker 环境运行
3. 包含并发安全测试

运行方式:
    docker exec quant-strategy-dev pytest tests/test_universe_pool.py -v
"""
import pytest
import asyncio
from datetime import datetime, date
from typing import List

import sys
sys.path.insert(0, '/app/src')

from database.stock_pool_models import UniverseStock, UniverseFilterConfig, PoolTransition
from services.stock_pool.universe_pool_service import UniversePoolService, universe_pool_service
from adapters.stock_data_provider import data_provider
from database import init_database, close_database


# Module-level setup
_db_initialized = False

async def ensure_db_initialized():
    """确保数据库已初始化"""
    global _db_initialized
    if not _db_initialized:
        await init_database()
        await data_provider.initialize()
        _db_initialized = True


class TestUniversePoolService:
    """Universe Pool 服务集成测试"""
    
    @pytest.mark.asyncio
    async def test_get_active_config(self):
        """测试获取活跃配置 - 使用真实数据库"""
        await ensure_db_initialized()
        await universe_pool_service.initialize()
        
        config = await universe_pool_service.get_active_config()
        
        # 验证配置存在且包含必要字段
        assert config is not None
        assert hasattr(config, 'min_list_months')
        assert hasattr(config, 'min_avg_turnover')
        assert hasattr(config, 'min_market_cap')
        assert hasattr(config, 'min_turnover_ratio')
        
        # 验证默认值合理
        assert config.min_list_months >= 1
        assert config.min_avg_turnover >= 0
        assert config.min_market_cap >= 0
        print(f"✓ Active config: {config.config_name}")
    
    @pytest.mark.asyncio
    async def test_update_filter_config(self):
        """测试动态更新筛选配置"""
        await ensure_db_initialized()
        await universe_pool_service.initialize()
        
        # 更新配置
        new_cap = 50.0
        updated = await universe_pool_service.update_filter_config(min_market_cap=new_cap)
        
        assert updated.min_market_cap == new_cap
        print(f"✓ Config updated: min_market_cap = {new_cap}")
        
        # 恢复默认
        await universe_pool_service.update_filter_config(min_market_cap=30.0)
    
    @pytest.mark.asyncio
    async def test_qualification_check_st_filter(self):
        """测试 ST 股票过滤规则"""
        await ensure_db_initialized()
        await universe_pool_service.initialize()
        
        from dateutil.relativedelta import relativedelta
        
        config = await universe_pool_service.get_active_config()
        min_list_date = date.today() - relativedelta(months=config.min_list_months)
        
        # ST 股票应被过滤
        st_stock = {
            'code': '000001',
            'name': '*ST测试',
            'list_date': '2020-01-01',
            'avg_turnover_20d': 5000,
            'market_cap': 100,
            'turnover_ratio_20d': 1.0
        }
        
        reason = universe_pool_service._check_qualification(st_stock, config, min_list_date)
        assert reason == "ST股票"
        print("✓ ST filter works correctly")
    
    @pytest.mark.asyncio
    async def test_qualification_check_market_cap_filter(self):
        """测试市值过滤规则"""
        await ensure_db_initialized()
        await universe_pool_service.initialize()
        
        from dateutil.relativedelta import relativedelta
        
        config = await universe_pool_service.get_active_config()
        min_list_date = date.today() - relativedelta(months=config.min_list_months)
        
        # 市值不足的股票应被过滤
        small_cap_stock = {
            'code': '000002',
            'name': '小市值测试',
            'list_date': '2020-01-01',
            'avg_turnover_20d': 5000,
            'market_cap': 10,  # 小于 30 亿
            'turnover_ratio_20d': 1.0
        }
        
        reason = universe_pool_service._check_qualification(small_cap_stock, config, min_list_date)
        assert "市值" in reason
        print("✓ Market cap filter works correctly")
    
    @pytest.mark.asyncio
    async def test_get_all_stocks_from_api(self):
        """测试从 get-stockdata 获取股票列表 - 真实 API 调用"""
        await ensure_db_initialized()
        
        stocks = await data_provider.get_all_stocks(limit=100)
        
        # 验证返回数据
        assert isinstance(stocks, list)
        print(f"✓ Fetched {len(stocks)} stocks from API")
        
        if stocks:
            sample = stocks[0]
            assert 'code' in sample or 'symbol' in sample
            print(f"✓ Sample stock: {sample.get('code', sample.get('symbol'))}")


class TestConcurrencySafety:
    """并发安全测试 - 验证 asyncio.Lock() 正确性"""
    
    @pytest.mark.asyncio
    async def test_concurrent_refresh_lock(self):
        """测试并发刷新时的锁机制"""
        await ensure_db_initialized()
        await universe_pool_service.initialize()
        
        # 模拟并发刷新请求
        async def refresh_task(task_id: int):
            print(f"Task {task_id} starting refresh...")
            result = await universe_pool_service.refresh_universe_pool(
                triggered_by=f"concurrent_test_{task_id}"
            )
            print(f"Task {task_id} finished: {result.success}")
            return result
        
        # 启动 3 个并发刷新任务
        tasks = [refresh_task(i) for i in range(3)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 验证所有任务完成 (不一定成功，但不应崩溃)
        completed_count = sum(1 for r in results if not isinstance(r, Exception))
        print(f"✓ {completed_count}/3 concurrent tasks completed without crash")
        
        # 至少应该有任务完成
        assert completed_count > 0


class TestAPIIntegration:
    """API 端点集成测试"""
    
    @pytest.mark.asyncio
    async def test_config_endpoint_response(self):
        """测试配置 API 端点响应格式"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get('http://localhost:8084/api/v1/pools/universe/config') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        assert 'config_name' in data
                        assert 'min_market_cap' in data
                        print(f"✓ Config API response valid: {data['config_name']}")
                    else:
                        pytest.skip(f"API not available (status {resp.status})")
            except aiohttp.ClientError:
                pytest.skip("API server not running")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
