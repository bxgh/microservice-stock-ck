"""
测试股票代码验证工具
"""
import pytest
from gsd_shared.validators import is_valid_a_stock


class TestIsValidAStock:
    """测试 is_valid_a_stock 函数"""
    
    def test_valid_shanghai_stocks(self):
        """测试有效的上海股票代码"""
        assert is_valid_a_stock("600519") == True  # 贵州茅台
        assert is_valid_a_stock("601318") == True  # 中国平安
        assert is_valid_a_stock("603259") == True
        assert is_valid_a_stock("605168") == True
        
    def test_valid_shenzhen_stocks(self):
        """测试有效的深圳股票代码"""
        assert is_valid_a_stock("000001") == True  # 平安银行
        assert is_valid_a_stock("000002") == True  # 万科A
        assert is_valid_a_stock("001979") == True
        assert is_valid_a_stock("002594") == True
        assert is_valid_a_stock("003816") == True
        
    def test_valid_chinext_stocks(self):
        """测试有效的创业板代码"""
        assert is_valid_a_stock("300059") == True  # 东方财富
        assert is_valid_a_stock("301238") == True
        
    def test_valid_star_market_stocks(self):
        """测试有效的科创板代码"""
        assert is_valid_a_stock("688001") == True
        assert is_valid_a_stock("688981") == True
        
    def test_invalid_b_stocks(self):
        """测试 B 股代码应被过滤"""
        assert is_valid_a_stock("200001") == False  # 深圳B股
        assert is_valid_a_stock("900901") == False  # 上海B股
        
    def test_invalid_delisted_stocks(self):
        """测试已退市股票（虽然前缀合法，但这里测试前缀规则）"""
        # 注意：000005 虽然已退市，但前缀 000 是合法的，所以会返回 True
        # 这是预期行为，退市状态需要通过其他数据源判断
        assert is_valid_a_stock("000005") == True  # 前缀合法
        
    def test_invalid_formats(self):
        """测试无效格式"""
        assert is_valid_a_stock("abc123") == False
        assert is_valid_a_stock("12345") == False   # 长度不足
        assert is_valid_a_stock("1234567") == False # 长度超出
        assert is_valid_a_stock("") == False
        assert is_valid_a_stock(None) == False
        assert is_valid_a_stock(123456) == False    # 非字符串
        
    def test_edge_cases(self):
        """测试边界情况"""
        assert is_valid_a_stock("600000") == True
        assert is_valid_a_stock("605999") == True
        assert is_valid_a_stock("688999") == True
        assert is_valid_a_stock("000000") == True
        assert is_valid_a_stock("003999") == True
        assert is_valid_a_stock("301999") == True
        
    def test_invalid_prefixes(self):
        """测试无效前缀"""
        assert is_valid_a_stock("400001") == False
        assert is_valid_a_stock("500001") == False
        assert is_valid_a_stock("700001") == False
        assert is_valid_a_stock("800001") == False
