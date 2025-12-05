"""
Dynamic Stock Pool Manager

Manages a dynamic list of stocks that are temporarily promoted for high-frequency collection.
Includes:
1. Automatically promoted stocks (from AnomalyDetector)
2. Manually added stocks (via API)
"""
import logging
import asyncio
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from zoneinfo import ZoneInfo
from .anomaly_detector import AnomalyStock

logger = logging.getLogger(__name__)

class DynamicPoolManager:
    """
    动态股票池管理器
    
    维护两个列表：
    1. promoted_stocks: 自动晋升的股票 (FIFO, 有容量限制)
    2. manual_stocks: 手动添加的股票 (无容量限制，有过期时间)
    """
    
    def __init__(self, max_dynamic_size: int = 10):
        self.max_dynamic_size = max_dynamic_size
        
        # 使用OrderedDict保证FIFO顺序: code -> AnomalyStock
        self.promoted_stocks: OrderedDict[str, AnomalyStock] = OrderedDict()
        
        # 手动添加的股票: code -> expire_at (datetime)
        self.manual_stocks: Dict[str, datetime] = {}
        
        # 线程安全锁
        self._lock = asyncio.Lock()
        
    async def promote(self, anomaly: AnomalyStock):
        """
        晋升股票到动态池
        
        Args:
            anomaly: 异动股票对象
        """
        async with self._lock:
            # 如果已存在，更新过期时间，并移动到末尾（视为最新）
            if anomaly.code in self.promoted_stocks:
                old = self.promoted_stocks[anomaly.code]
                # 取两者中较晚的过期时间
                if anomaly.expire_at > old.expire_at:
                    old.expire_at = anomaly.expire_at
                
                # 移动到末尾
                self.promoted_stocks.move_to_end(anomaly.code)
                logger.info(f"🔄 更新晋升股票 {anomaly.code} 过期时间至 {old.expire_at}")
                return
            
            # 如果超出最大数量，移除最早的（FIFO）
            if len(self.promoted_stocks) >= self.max_dynamic_size:
                oldest_code, _ = self.promoted_stocks.popitem(last=False)
                logger.warning(f"⚠️ 动态池已满，移除最早晋升股票: {oldest_code}")
            
            # 添加新股票
            self.promoted_stocks[anomaly.code] = anomaly
            logger.info(f"✅ 晋升股票到动态池: {anomaly.code} ({anomaly.trigger_reason})")
    
    async def add_manual(self, code: str, duration_minutes: int = 60):
        """
        手动添加股票到监控池
        
        Args:
            code: 股票代码
            duration_minutes: 持续监控时间（分钟）
        """
        async with self._lock:
            expire_at = datetime.now(ZoneInfo("Asia/Shanghai")) + timedelta(minutes=duration_minutes)
            self.manual_stocks[code] = expire_at
            logger.info(f"👉 手动添加股票: {code}, 过期时间: {expire_at}")
    
    async def remove_manual(self, code: str):
        """
        移除手动添加的股票
        
        Args:
            code: 股票代码
        """
        async with self._lock:
            if code in self.manual_stocks:
                del self.manual_stocks[code]
                logger.info(f"🗑️ 移除手动股票: {code}")
    
    async def cleanup_expired(self):
        """清理过期的股票"""
        async with self._lock:
            now = datetime.now(ZoneInfo("Asia/Shanghai"))
            
            # 清理过期的晋升股票
            expired_promoted = [
                code for code, anomaly in self.promoted_stocks.items()
                if anomaly.expire_at < now
            ]
            for code in expired_promoted:
                del self.promoted_stocks[code]
                logger.info(f"⏰ 移除过期晋升股票: {code}")
            
            # 清理过期的手动股票
            expired_manual = [
                code for code, expire_at in self.manual_stocks.items()
                if expire_at < now
            ]
            for code in expired_manual:
                del self.manual_stocks[code]
                logger.info(f"⏰ 移除过期手动股票: {code}")
    
    async def get_all_dynamic_stocks(self) -> List[str]:
        """
        获取所有动态股票（晋升 + 手动）
        
        Returns:
            List[str]: 股票代码列表（去重）
        """
        async with self._lock:
            promoted = list(self.promoted_stocks.keys())
            manual = list(self.manual_stocks.keys())
            # 合并去重
            return list(set(promoted + manual))
    
    async def get_stats(self) -> dict:
        """获取统计信息"""
        async with self._lock:
            return {
                "promoted_count": len(self.promoted_stocks),
                "manual_count": len(self.manual_stocks),
                "total_dynamic": len(self.promoted_stocks) + len(self.manual_stocks),
                "max_capacity": self.max_dynamic_size,
                "promoted_list": [
                    {
                        "code": s.code, 
                        "reason": s.trigger_reason, 
                        "expire_at": s.expire_at.isoformat()
                    } 
                    for s in self.promoted_stocks.values()
                ],
                "manual_list": [
                    {"code": c, "expire_at": t.isoformat()} 
                    for c, t in self.manual_stocks.items()
                ]
            }
