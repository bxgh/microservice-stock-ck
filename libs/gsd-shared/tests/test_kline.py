"""
测试 KLineRecord 模型
"""

import pytest
from datetime import date
from gsd_shared.models import KLineRecord


def test_kline_creation():
    """测试直接创建 K线记录"""
    record = KLineRecord(
        stock_code="000001",
        trade_date=date(2024, 1, 2),
        open_price=10.5,
        high_price=11.0,
        low_price=10.2,
        close_price=10.8,
        volume=1000000,
        amount=10800000,
        turnover_rate=2.5,
        change_pct=2.86
    )
    
    assert record.stock_code == "000001"
    assert record.close_price == 10.8
    assert record.volume == 1000000


def test_kline_from_mysql():
    """测试从 MySQL 数据创建"""
    mysql_row = {
        'code': '600519',
        'trade_date': date(2024, 1, 2),
        'open': 1800.0,
        'high': 1850.0,
        'low': 1790.0,
        'close': 1820.0,
        'volume': 5000000,
        'amount': 9100000000,
        'turnover': 1.5,
        'pct_chg': 1.11
    }
    
    record = KLineRecord.from_mysql(mysql_row)
    
    assert record.stock_code == "600519"
    assert record.open_price == 1800.0
    assert record.turnover_rate == 1.5
    assert record.change_pct == 1.11


def test_kline_to_clickhouse_dict():
    """测试转换为 ClickHouse 字典"""
    record = KLineRecord(
        stock_code="000001",
        trade_date=date(2024, 1, 2),
        open_price=10.5,
        high_price=11.0,
        low_price=10.2,
        close_price=10.8,
        volume=1000000,
        amount=10800000
    )
    
    ch_dict = record.to_clickhouse_dict()
    
    assert ch_dict['stock_code'] == "000001"
    assert ch_dict['open_price'] == 10.5
    assert 'turnover_rate' in ch_dict
