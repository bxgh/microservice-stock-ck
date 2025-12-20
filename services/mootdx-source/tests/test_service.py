"""
Unit Tests for mootdx-source Service

测试覆盖:
- 路由表配置
- 数据源初始化
- 降级策略
- 错误处理
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pandas as pd

# Mock protobuf before importing
import sys
sys.path.insert(0, '/app/libs/common')

from datasource.v1 import data_source_pb2
from services.mootdx-source.src.service import MooTDXService, RouteConfig
from services.mootdx-source.src.config import DataSource


class TestMooTDXService:
    """测试 MooTDXService"""
    
    @pytest.fixture
    async def service(self):
        """创建测试服务实例"""
        svc = MooTDXService()
        # Mock 数据源初始化
        svc.mootdx_client = Mock()
        svc.easyquotation_client = Mock()
        svc.cloud_client = AsyncMock()
        yield svc
        await svc.close()
    
    def test_routing_table_completeness(self):
        """测试路由表是否完整"""
        # 所有 DataType 都应该有对应的路由配置
        expected_types = [
            data_source_pb2.DATA_TYPE_QUOTES,
            data_source_pb2.DATA_TYPE_TICK,
            data_source_pb2.DATA_TYPE_HISTORY,
            data_source_pb2.DATA_TYPE_RANKING,
            data_source_pb2.DATA_TYPE_SECTOR,
            data_source_pb2.DATA_TYPE_FINANCE,
            data_source_pb2.DATA_TYPE_VALUATION,
            data_source_pb2.DATA_TYPE_INDEX,
            data_source_pb2.DATA_TYPE_INDUSTRY,
        ]
        
        for dtype in expected_types:
            assert dtype in MooTDXService.ROUTING_TABLE, f"Missing route for {dtype}"
            route = MooTDXService.ROUTING_TABLE[dtype]
            assert isinstance(route, RouteConfig)
            assert route.handler
            assert route.source_name
    
    @pytest.mark.asyncio
    async def test_fetch_quotes_success(self, service):
        """测试行情数据获取成功"""
        # Mock mootdx 返回数据
        mock_df = pd.DataFrame({
            'code': ['000001', '600519'],
            'name': ['平安银行', '贵州茅台'],
            'price': [11.53, 1433.10]
        })
        
        with patch.object(service, '_fetch_quotes_mootdx', return_value=mock_df):
            request = data_source_pb2.DataRequest(
                type=data_source_pb2.DATA_TYPE_QUOTES,
                codes=['000001', '600519']
            )
            
            response = await service.FetchData(request, None)
            
            assert response.success is True
            assert response.source_name == DataSource.MOOTDX
            assert len(response.json_data) > 0
    
    @pytest.mark.asyncio
    async def test_fallback_strategy(self, service):
        """测试降级策略"""
        # Mock 云端 API 失败
        service.cloud_client.fetch_baostock = AsyncMock(return_value=pd.DataFrame())
        
        # Mock 本地降级成功
        mock_df = pd.DataFrame({'date': ['2024-01-01'], 'close': [100.0]})
        
        with patch.object(service, '_fetch_history_mootdx', return_value=mock_df):
            request = data_source_pb2.DataRequest(
                type=data_source_pb2.DATA_TYPE_HISTORY,
                codes=['600519'],
                params={'start_date': '2024-01-01', 'end_date': '2024-12-31'}
            )
            
            response = await service.FetchData(request, None)
            
            # 应该降级到本地数据源
            assert response.success is True
            assert 'fallback' in response.source_name or len(response.json_data) > 2
    
    @pytest.mark.asyncio
    async def test_error_handling(self, service):
        """测试错误处理"""
        # Mock 处理器抛出异常
        with patch.object(service, '_fetch_quotes_mootdx', side_effect=ValueError("Test error")):
            request = data_source_pb2.DataRequest(
                type=data_source_pb2.DATA_TYPE_QUOTES,
                codes=['000001']
            )
            
            response = await service.FetchData(request, None)
            
            assert response.success is False
            assert 'Test error' in response.error_message or response.error_message
    
    @pytest.mark.asyncio
    async def test_unsupported_datatype(self, service):
        """测试不支持的 DataType"""
        # 使用一个不存在的 DataType
        request = data_source_pb2.DataRequest(
            type=999,  # 无效类型
            codes=['000001']
        )
        
        response = await service.FetchData(request, None)
        
        assert response.success is False
        assert 'Unsupported' in response.error_message
    
    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """测试健康检查"""
        request = data_source_pb2.Empty()
        response = await service.HealthCheck(request, None)
        
        assert response.healthy is True
        assert 'healthy' in response.message.lower()
    
    @pytest.mark.asyncio
    async def test_get_capabilities(self, service):
        """测试能力查询"""
        request = data_source_pb2.Empty()
        response = await service.GetCapabilities(request, None)
        
        assert len(response.supported_types) == 10  # 增加到10个（包含龙虎榜）
        assert response.version == "2.0.0-hybrid"
    
    # === 龙虎榜数据测试 ===
    
    @pytest.mark.asyncio
    async def test_fetch_dragon_tiger_success(self, service):
        """测试龙虎榜数据获取成功"""
        # Mock 返回数据
        mock_df = pd.DataFrame({
            'code': ['000001', '600519'],
            'name': ['平安银行', '贵州茅台'],
            'close_price': [11.53, 1433.10],
            'change_pct': [5.12, 2.34],
            'lhb_reason': ['日涨幅偏离值达7%', '日振幅达15%'],
            'buy_total': [50000000, 80000000],
            'sell_total': [30000000, 60000000]
        })
        
        with patch.object(service, '_fetch_dragon_tiger_akshare', return_value=mock_df):
            request = data_source_pb2.DataRequest(
                type=data_source_pb2.DATA_TYPE_META,
                codes=['000001', '600519'],
                params={'date': '2025-12-17', 'market': '沪深'}
            )
            
            response = await service.FetchData(request, None)
            
            assert response.success is True
            assert response.source_name == "akshare-api"
            assert response.latency_ms > 0
            
            # 验证返回数据
            import json
            data = json.loads(response.json_data)
            assert len(data) == 2
            assert data[0]['code'] == '000001'
            assert data[0]['lhb_reason'] == '日涨幅偏离值达7%'
    
    @pytest.mark.asyncio
    async def test_fetch_dragon_tiger_all_stocks(self, service):
        """测试获取全部龙虎榜数据（不指定股票代码）"""
        mock_df = pd.DataFrame({
            'code': ['000001', '600519', '000002'],
            'name': ['平安银行', '贵州茅台', '万科A']
        })
        
        with patch.object(service, '_fetch_dragon_tiger_akshare', return_value=mock_df):
            request = data_source_pb2.DataRequest(
                type=data_source_pb2.DATA_TYPE_META,
                codes=[],  # 不指定代码，获取全部
                params={'date': '2025-12-17'}
            )
            
            response = await service.FetchData(request, None)
            
            assert response.success is True
            import json
            data = json.loads(response.json_data)
            assert len(data) == 3  # 返回全部
    
    @pytest.mark.asyncio
    async def test_fetch_dragon_tiger_api_error(self, service):
        """测试龙虎榜 API 错误处理"""
        # Mock API 返回错误
        service.cloud_client.fetch_akshare = AsyncMock(
            side_effect=ConnectionError("API unavailable")
        )
        
        request = data_source_pb2.DataRequest(
            type=data_source_pb2.DATA_TYPE_META,
            codes=['000001']
        )
        
        response = await service.FetchData(request, None)
        
        # 应正确处理错误
        assert response.success is False or response.json_data == "[]"


class TestCloudClient:
    """测试 CloudAPIClient"""
    
    @pytest.mark.asyncio
    async def test_retry_on_network_error(self):
        """测试网络错误时的重试机制"""
        from services.mootdx-source.src.cloud_client import CloudAPIClient
        
        client = CloudAPIClient()
        await client.initialize()
        
        # Mock session 返回 500 错误
        with patch.object(client.session, 'get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Server Error")
            mock_get.return_value.__aenter__.return_value = mock_response
            
            with pytest.raises(ConnectionError):
                await client._fetch("http://test.com/api")
        
        await client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
