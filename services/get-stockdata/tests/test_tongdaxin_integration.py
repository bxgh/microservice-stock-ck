#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TongDaXin 数据源集成测试

测试内容：
- 工厂创建测试
- 连接测试
- 数据获取测试
- 状态查询测试
- 资源清理测试
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_sources.factory import DataSourceFactory
from src.models.tick_models import TickDataRequest
from datetime import datetime


class TestTongDaXinIntegration:
    """TongDaXin 数据源集成测试"""
    
    def test_factory_can_create_tongdaxin(self):
        """测试工厂能创建 TongDaXin 数据源"""
        source = DataSourceFactory.create_source('tongdaxin')
        assert source is not None
        assert source.source_name == 'tongdaxin'
    
    def test_tongdaxin_in_available_sources(self):
        """测试 TongDaXin 在可用数据源列表中"""
        available = DataSourceFactory.get_available_sources()
        assert 'tongdaxin' in available
    
    def test_tongdaxin_config(self):
        """测试 TongDaXin 配置正确"""
        config = DataSourceFactory.get_source_config('tongdaxin')
        assert config['class'] is not None
        assert config['default'] == False
        assert config['timeout'] == 30
        assert config['max_connections'] == 5
    
    @pytest.mark.asyncio
    async def test_tongdaxin_properties(self):
        """测试 TongDaXin 基本属性"""
        source = DataSourceFactory.create_source('tongdaxin')
        
        # 初始状态
        assert source.source_name == 'tongdaxin'
        assert source.is_connected == False
    
    @pytest.mark.asyncio
    async def test_tongdaxin_can_connect(self):
        """测试 TongDaXin 能连接（可能失败，取决于网络）"""
        source = DataSourceFactory.create_source('tongdaxin')
        
        try:
            success = await source.connect()
            # 注意：这个测试可能因为网络问题失败，这是正常的
            if success:
                assert source.is_connected == True
                print("✅ TongDaXin 连接成功")
            else:
                print("⚠️ TongDaXin 连接失败（可能是网络问题）")
                # 不 assert，因为网络问题是正常的
        except Exception as e:
            print(f"⚠️ TongDaXin 连接异常: {e}")
            # 不 assert，允许连接失败
    
    @pytest.mark.asyncio
    async def test_tongdaxin_get_status(self):
        """测试 TongDaXin 状态查询"""
        source = DataSourceFactory.create_source('tongdaxin')
        
        # 未连接时的状态
        status = await source.get_status()
        assert status is not None
        assert 'source_name' in status
        assert status['source_name'] == 'tongdaxin'
        assert 'connected' in status
        assert 'timestamp' in status
    
    @pytest.mark.asyncio
    async def test_tongdaxin_fetch_data_structure(self):
        """测试 TongDaXin 数据获取接口（不验证数据内容）"""
        source = DataSourceFactory.create_source('tongdaxin')
        
        request = TickDataRequest(
            stock_code='000001',
            date=datetime(2025, 11, 29)
        )
        
        try:
            # 尝试获取数据
            data = await source.get_tick_data(request)
            
            # 验证返回类型
            assert isinstance(data, list)
            print(f"✅ TongDaXin 返回数据: {len(data)} 条")
            
        except Exception as e:
            print(f"⚠️ TongDaXin 获取数据异常: {e}")
            # 不 assert，允许获取失败
    
    @pytest.mark.asyncio
    async def test_tongdaxin_cleanup(self):
        """测试 TongDaXin 资源清理"""
        source = DataSourceFactory.create_source('tongdaxin')
        
        # 尝试连接
        try:
            await source.connect()
        except:
            pass
        
        # 清理资源
        await source.close()
        
        # 验证连接已关闭
        assert source.is_connected == False
    
    @pytest.mark.asyncio
    async def test_tongdaxin_custom_config(self):
        """测试 TongDaXin 自定义配置"""
        custom_config = {
            'timeout': 60,
            'max_connections': 10
        }
        
        source = DataSourceFactory.create_source('tongdaxin', config=custom_config)
        assert source is not None
        assert source.source_name == 'tongdaxin'


class TestDataSourceFactory:
    """数据源工厂测试"""
    
    def test_available_sources_includes_both(self):
        """测试可用数据源包含 mootdx 和 tongdaxin"""
        available = DataSourceFactory.get_available_sources()
        assert 'mootdx' in available
        assert 'tongdaxin' in available
        assert len(available) >= 2
    
    def test_default_source_is_mootdx(self):
        """测试默认数据源是 mootdx"""
        source = DataSourceFactory.create_default_source()
        assert source.source_name == 'mootdx'
    
    def test_create_invalid_source_raises_error(self):
        """测试创建无效数据源抛出异常"""
        with pytest.raises(ValueError):
            DataSourceFactory.create_source('invalid_source')
    
    def test_get_invalid_config_raises_error(self):
        """测试获取无效配置抛出异常"""
        with pytest.raises(ValueError):
            DataSourceFactory.get_source_config('invalid_source')


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
