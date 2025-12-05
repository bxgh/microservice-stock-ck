"""
Anomaly Detector for Stock Market Data

Detects abnormal stock movements based on:
1. Price surge in short time window (e.g., > 3% in 5 mins)
2. High turnover rate (e.g., > 1% in 5 mins)
"""
import logging
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from zoneinfo import ZoneInfo
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class AnomalyStock:
    """异动股票数据类"""
    code: str
    name: str
    trigger_reason: str  # "涨幅" or "换手率"
    trigger_value: float
    detected_at: datetime
    expire_at: datetime

class AnomalyDetector:
    """
    异动股票检测器
    
    维护最近N分钟的价格历史，用于计算短时涨跌幅。
    """
    
    def __init__(self, 
                 price_change_threshold: float = 3.0,
                 turnover_threshold: float = 1.0,
                 detection_window: int = 5,  # 分钟
                 promotion_duration: int = 30):  # 分钟
        
        self.price_change_threshold = price_change_threshold
        self.turnover_threshold = turnover_threshold
        self.detection_window = detection_window
        self.promotion_duration = promotion_duration
        
        # 历史数据缓存: code -> List[dict]
        # dict structure: {"price": float, "turnover": float, "timestamp": datetime}
        self.history: Dict[str, List[dict]] = {}
        
        # 线程安全锁
        self._lock = asyncio.Lock()
        
    async def detect_anomalies(self, latest_data: pd.DataFrame) -> List[AnomalyStock]:
        """
        检测异动股票
        
        Args:
            latest_data: 包含最新行情的DataFrame，需包含字段: 代码, 名称, 最新价, 涨跌幅, 换手率
            
        Returns:
            List[AnomalyStock]: 检测到的异动股票列表
        """
        anomalies = []
        
        # 确保DataFrame不为空
        if latest_data.empty:
            return []
            
        async with self._lock:
            current_time = datetime.now(ZoneInfo("Asia/Shanghai"))
            
            for _, row in latest_data.iterrows():
                try:
                    code = str(row["代码"])
                    name = str(row["名称"])
                    current_price = float(row["最新价"])
                    current_turnover = float(row.get("换手率", 0))
                    
                    # 准备行数据字典
                    row_dict = {
                        "代码": code,
                        "名称": name,
                        "最新价": current_price,
                        "涨跌幅": float(row.get("涨跌幅", 0)),
                        "换手率": current_turnover
                    }
                    
                    # 更新历史数据
                    self._update_history(code, row_dict, current_time)
                    
                    # 1. 检查涨幅异动
                    is_price_anomaly, price_change = self._check_price_change(code, row_dict, current_time)
                    if is_price_anomaly:
                        anomaly = AnomalyStock(
                            code=code,
                            name=name,
                            trigger_reason="涨幅",
                            trigger_value=price_change,
                            detected_at=current_time,
                            expire_at=current_time + timedelta(minutes=self.promotion_duration)
                        )
                        anomalies.append(anomaly)
                        logger.info(f"🔥 异动检测: {code} {name} 5分钟涨幅 {price_change:.2f}% > {self.price_change_threshold}%")
                        continue  # 优先涨幅
                    
                    # 2. 检查换手率异动
                    is_turnover_anomaly, turnover_change = self._check_turnover_rate(code, row_dict, current_time)
                    if is_turnover_anomaly:
                        anomaly = AnomalyStock(
                            code=code,
                            name=name,
                            trigger_reason="换手率",
                            trigger_value=turnover_change,
                            detected_at=current_time,
                            expire_at=current_time + timedelta(minutes=self.promotion_duration)
                        )
                        anomalies.append(anomaly)
                        logger.info(f"🔥 异动检测: {code} {name} 5分钟换手率增量 {turnover_change:.2f}% > {self.turnover_threshold}%")
                        
                except Exception as e:
                    logger.error(f"处理股票 {row.get('代码', 'unknown')} 异动检测时出错: {e}")
                    continue
            
            # 清理过期的历史数据
            self._cleanup_history(current_time)
            
        return anomalies
    
    def _update_history(self, code: str, current_row: dict, current_time: datetime):
        """更新历史数据"""
        if code not in self.history:
            self.history[code] = []
            
        self.history[code].append({
            "price": current_row["最新价"],
            "turnover": current_row["换手率"],
            "timestamp": current_time
        })

    def _check_price_change(self, code: str, current_row: dict, current_time: datetime) -> tuple[bool, float]:
        """
        检查5分钟涨幅是否超过阈值
        """
        # 获取检测窗口内的最早数据
        cutoff_time = current_time - timedelta(minutes=self.detection_window)
        
        # 过滤出窗口内的数据
        window_data = [p for p in self.history[code] if p["timestamp"] > cutoff_time]
        
        # 如果历史数据不足（至少需要2个点），无法判断
        if len(window_data) < 2:
            return False, 0.0
        
        # 计算涨幅：(当前价格 - 窗口内最早价格) / 窗口内最早价格
        oldest_price = window_data[0]["price"]
        current_price = current_row["最新价"]
        
        if oldest_price == 0:
            return False, 0.0
        
        change_pct = ((current_price - oldest_price) / oldest_price) * 100
        
        return change_pct > self.price_change_threshold, change_pct
    
    def _check_turnover_rate(self, code: str, current_row: dict, current_time: datetime) -> tuple[bool, float]:
        """
        检查5分钟换手率增量是否超过阈值
        """
        # 获取检测窗口内的最早数据
        cutoff_time = current_time - timedelta(minutes=self.detection_window)
        
        # 过滤出窗口内的数据
        window_data = [p for p in self.history[code] if p["timestamp"] > cutoff_time]
        
        if len(window_data) < 2:
            return False, 0.0
            
        # 计算换手率增量：当前累计换手率 - 5分钟前累计换手率
        # 注意：换手率通常是当日累计值，所以直接相减即可得到区间换手率
        oldest_turnover = window_data[0]["turnover"]
        current_turnover = current_row["换手率"]
        
        turnover_delta = current_turnover - oldest_turnover
        
        # 处理可能的异常情况（如数据重置）
        if turnover_delta < 0:
            return False, 0.0
            
        return turnover_delta > self.turnover_threshold, turnover_delta
        
    def _cleanup_history(self, current_time: datetime):
        """清理过期的历史数据"""
        cutoff_time = current_time - timedelta(minutes=self.detection_window * 2)
        
        for code in list(self.history.keys()):
            self.history[code] = [
                p for p in self.history[code] 
                if p["timestamp"] > cutoff_time
            ]
            
            if not self.history[code]:
                del self.history[code]
