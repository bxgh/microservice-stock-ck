# -*- coding: utf-8 -*-
"""
TimeAwareStrategy 单元测试

@author: EPIC-007 Story 007.07
@date: 2025-12-07
"""

import pytest
from datetime import time
from src.data_services.time_aware_strategy import TimeAwareStrategy, get_time_strategy


class TestTimeAwareStrategy:
    """时段感知策略测试"""
    
    def test_import(self):
        """测试导入"""
        assert TimeAwareStrategy is not None
    
    def test_singleton(self):
        """测试单例"""
        s1 = get_time_strategy()
        s2 = get_time_strategy()
        assert s1 is s2
    
    def test_get_session(self):
        """测试时段获取"""
        strategy = TimeAwareStrategy()
        session = strategy.get_session()
        
        # 返回有效时段
        assert session in ['pre_market', 'trading', 'lunch', 'after_hours']
    
    def test_cache_ttl_types(self):
        """测试缓存TTL数据类型"""
        strategy = TimeAwareStrategy()
        
        # 测试各数据类型
        data_types = ['quotes', 'tick', 'ranking', 'sector_ranking', 'history']
        for dt in data_types:
            ttl = strategy.get_cache_ttl(dt)
            assert isinstance(ttl, int)
            assert ttl > 0
    
    def test_source_priority(self):
        """测试数据源优先级"""
        strategy = TimeAwareStrategy()
        
        sources = strategy.get_source_priority('quotes')
        assert isinstance(sources, list)
    
    def test_session_info(self):
        """测试时段信息"""
        strategy = TimeAwareStrategy()
        
        info = strategy.get_session_info()
        
        assert 'time' in info
        assert 'session' in info
        assert 'is_trading' in info
        assert 'is_weekend' in info
    
    def test_unknown_data_type(self):
        """测试未知数据类型"""
        strategy = TimeAwareStrategy()
        
        # 应返回默认值
        ttl = strategy.get_cache_ttl('unknown_type')
        assert ttl > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
