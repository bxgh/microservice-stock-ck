"""
Test AnomalyDetector
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
from services.stock_pool.anomaly_detector import AnomalyDetector, AnomalyStock

@pytest.mark.asyncio
async def test_detect_price_change_anomaly():
    """测试涨幅异动检测"""
    detector = AnomalyDetector(price_change_threshold=3.0, detection_window=5)
    
    # 模拟时间
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    
    # 1. 初始数据 (T=0)
    data_t0 = pd.DataFrame([
        {"代码": "000001", "名称": "平安银行", "最新价": 10.0, "涨跌幅": 0.0, "换手率": 0.1}
    ])
    
    # 第一次检测，应该没有异动（历史数据不足）
    anomalies = await detector.detect_anomalies(data_t0)
    assert len(anomalies) == 0
    
    # 2. 3分钟后 (T=3)
    # 价格上涨到 10.2 (2%)
    data_t3 = pd.DataFrame([
        {"代码": "000001", "名称": "平安银行", "最新价": 10.2, "涨跌幅": 2.0, "换手率": 0.2}
    ])
    
    # 模拟时间流逝（通过mock或直接修改detector内部逻辑，这里简单起见，我们假设detector使用系统时间，
    # 但为了测试稳定，我们在detector中使用了datetime.now()。
    # 在单元测试中，最好mock datetime。
    # 这里为了简单，我们直接修改detector.history中的时间戳
    detector.history["000001"][0]["timestamp"] = now - timedelta(minutes=3)
    
    anomalies = await detector.detect_anomalies(data_t3)
    assert len(anomalies) == 0 # 2% < 3%
    
    # 3. 5分钟后 (T=5)
    # 价格上涨到 10.4 (4%)
    data_t5 = pd.DataFrame([
        {"代码": "000001", "名称": "平安银行", "最新价": 10.4, "涨跌幅": 4.0, "换手率": 0.3}
    ])
    
    # 修改历史时间戳 (确保在窗口内，使用 4.9 分钟)
    detector.history["000001"][0]["timestamp"] = now - timedelta(minutes=4.9)
    detector.history["000001"][1]["timestamp"] = now - timedelta(minutes=2)
    
    anomalies = await detector.detect_anomalies(data_t5)
    assert len(anomalies) == 1
    assert anomalies[0].code == "000001"
    assert anomalies[0].trigger_reason == "涨幅"
    assert anomalies[0].trigger_value > 3.0

@pytest.mark.asyncio
async def test_detect_turnover_anomaly():
    """测试换手率异动检测"""
    detector = AnomalyDetector(turnover_threshold=1.0, detection_window=5)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    
    # 1. 初始数据
    data_t0 = pd.DataFrame([
        {"代码": "600000", "名称": "浦发银行", "最新价": 10.0, "涨跌幅": 0.0, "换手率": 0.5}
    ])
    await detector.detect_anomalies(data_t0)
    
    # 2. 5分钟后，换手率激增到 1.6 (增量 1.1 > 1.0)
    data_t5 = pd.DataFrame([
        {"代码": "600000", "名称": "浦发银行", "最新价": 10.0, "涨跌幅": 0.0, "换手率": 1.6}
    ])
    
    # 修改历史时间戳 (确保在窗口内)
    detector.history["600000"][0]["timestamp"] = now - timedelta(minutes=4.9)
    
    anomalies = await detector.detect_anomalies(data_t5)
    assert len(anomalies) == 1
    assert anomalies[0].trigger_reason == "换手率"
    assert anomalies[0].trigger_value > 1.0

@pytest.mark.asyncio
async def test_history_cleanup():
    """测试历史数据清理"""
    detector = AnomalyDetector(detection_window=5)
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    
    # 添加过期数据 (15分钟前)
    detector.history["000001"] = [{
        "price": 10.0, 
        "turnover": 0.1, 
        "timestamp": now - timedelta(minutes=15)
    }]
    
    # 触发一次检测
    data = pd.DataFrame([
        {"代码": "000001", "名称": "平安银行", "最新价": 10.0, "涨跌幅": 0.0, "换手率": 0.1}
    ])
    
    await detector.detect_anomalies(data)
    
    # 应该只剩最新的1条数据，旧的被清理
    assert len(detector.history["000001"]) == 1
    # 实际上，detect_anomalies会先添加新数据，然后清理旧数据
    # 如果旧数据超过 detection_window * 2 (10分钟)，会被清理
    # 15分钟 > 10分钟，应该被清理
