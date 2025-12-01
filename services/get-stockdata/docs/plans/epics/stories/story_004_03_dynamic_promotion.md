# Story 004.03: 动态晋升机制

**Epic**: EPIC-004 股票池动态管理  
**优先级**: P1  
**预估工期**: 2 天  
**状态**: 📝 待开始  
**前置依赖**: Story 004.01

---

## 📋 Story 描述

**作为** 交易员  
**我希望** 系统能自动识别异动股票并临时加入高频采集池  
**以便** 及时捕捉妖股启动的宝贵数据

---

## 🎯 验收标准

### 功能需求
- [ ] 实现 5 分钟涨幅 > 3% 的自动晋升
- [ ] 实现 5 分钟换手率 > 1% 的自动晋升
- [ ] 晋升股票临时进入 L1 池（30 分钟），不挤出原有股票
- [ ] 支持手动添加紧急监控股票

### 性能需求
- [ ] 异动检测延迟 < 10 秒
- [ ] 晋升股票立即参与下一轮采集
- [ ] 支持同时晋升多只股票（最多10只）

### 测试需求
- [ ] 单元测试覆盖晋升/降级逻辑
- [ ] 模拟异动场景测试
- [ ] 验证时间窗口过期机制

---

## 🔧 技术设计

### 1. 异动检测器

```python
# src/services/stock_pool/anomaly_detector.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd

@dataclass
class AnomalyStock:
    """异动股票"""
    code: str
    name: str
    trigger_reason: str  # "涨幅" or "换手率"
    trigger_value: float
    detected_at: datetime
    expire_at: datetime

class AnomalyDetector:
    """异动股票检测器"""
    
    def __init__(self, 
                 price_change_threshold: float = 3.0,
                 turnover_threshold: float = 1.0,
                 detection_window: int = 5,  # 分钟
                 promotion_duration: int = 30):  # 分钟
        self.price_change_threshold = price_change_threshold
        self.turnover_threshold = turnover_threshold
        self.detection_window = detection_window
        self.promotion_duration = promotion_duration
        
        # 历史数据缓存（用于计算5分钟变化）
        self.price_history: Dict[str, List[dict]] = {}
        
    async def detect_anomalies(self, latest_data: pd.DataFrame) -> List[AnomalyStock]:
        """检测异动股票"""
        anomalies = []
        
        for _, row in latest_data.iterrows():
            code = row["代码"]
            
            # 检查涨幅异动
            if await self._check_price_change(code, row):
                anomaly = AnomalyStock(
                    code=code,
                    name=row["名称"],
                    trigger_reason="涨幅",
                    trigger_value=row["涨跌幅"],
                    detected_at=datetime.now(),
                    expire_at=datetime.now() + timedelta(minutes=self.promotion_duration)
                )
                anomalies.append(anomaly)
                logger.info(f"异动检测: {code} {row['名称']} 涨幅 {row['涨跌幅']:.2f}%")
            
            # 检查换手率异动
            elif await self._check_turnover_rate(code, row):
                anomaly = AnomalyStock(
                    code=code,
                    name=row["名称"],
                    trigger_reason="换手率",
                    trigger_value=row["换手率"],
                    detected_at=datetime.now(),
                    expire_at=datetime.now() + timedelta(minutes=self.promotion_duration)
                )
                anomalies.append(anomaly)
                logger.info(f"异动检测: {code} {row['名称']} 换手率 {row['换手率']:.2f}%")
        
        return anomalies
    
    async def _check_price_change(self, code: str, current_row: dict) -> bool:
        """检查5分钟涨幅是否超过阈值"""
        if code not in self.price_history:
            self.price_history[code] = []
        
        # 添加当前价格到历史
        self.price_history[code].append({
            "price": current_row["最新价"],
            "timestamp": datetime.now()
        })
        
        # 只保留最近5分钟的数据
        cutoff_time = datetime.now() - timedelta(minutes=self.detection_window)
        self.price_history[code] = [
            p for p in self.price_history[code] 
            if p["timestamp"] > cutoff_time
        ]
        
        # 如果历史数据不足，无法判断
        if len(self.price_history[code]) < 2:
            return False
        
        # 计算5分钟涨幅
        oldest_price = self.price_history[code][0]["price"]
        current_price = current_row["最新价"]
        
        if oldest_price == 0:
            return False
        
        change_pct = ((current_price - oldest_price) / oldest_price) * 100
        
        return change_pct > self.price_change_threshold
    
    async def _check_turnover_rate(self, code: str, current_row: dict) -> bool:
        """检查5分钟换手率是否超过阈值"""
        # 简化实现：直接使用当前换手率
        # 实际应该计算5分钟内的累计换手率
        return current_row.get("换手率", 0) > self.turnover_threshold
```

### 2. 动态池管理器

```python
# src/services/stock_pool/dynamic_pool_manager.py
from collections import OrderedDict

class DynamicPoolManager:
    """动态股票池管理器"""
    
    def __init__(self, max_dynamic_size: int = 10):
        self.max_dynamic_size = max_dynamic_size
        # 使用OrderedDict保证FIFO顺序
        self.promoted_stocks: OrderedDict[str, AnomalyStock] = OrderedDict()
        self.manual_stocks: Dict[str, datetime] = {}  # 手动添加的股票
        self._lock = asyncio.Lock()
    
    async def promote(self, anomaly: AnomalyStock):
        """晋升股票到动态池"""
        async with self._lock:
            # 如果已存在，更新过期时间
            if anomaly.code in self.promoted_stocks:
                old = self.promoted_stocks[anomaly.code]
                old.expire_at = anomaly.expire_at
                logger.info(f"更新晋升股票 {anomaly.code} 过期时间")
                return
            
            # 如果超出最大数量，移除最早的
            if len(self.promoted_stocks) >= self.max_dynamic_size:
                oldest_code, oldest = self.promoted_stocks.popitem(last=False)
                logger.warning(f"动态池已满，移除最早晋升股票: {oldest_code}")
            
            # 添加新股票
            self.promoted_stocks[anomaly.code] = anomaly
            logger.info(f"晋升股票到动态池: {anomaly.code} ({anomaly.trigger_reason})")
    
    async def add_manual(self, code: str, duration_minutes: int = 60):
        """手动添加股票到监控池"""
        async with self._lock:
            expire_at = datetime.now() + timedelta(minutes=duration_minutes)
            self.manual_stocks[code] = expire_at
            logger.info(f"手动添加股票: {code}, 过期时间: {expire_at}")
    
    async def remove_manual(self, code: str):
        """移除手动添加的股票"""
        async with self._lock:
            if code in self.manual_stocks:
                del self.manual_stocks[code]
                logger.info(f"移除手动股票: {code}")
    
    async def cleanup_expired(self):
        """清理过期的股票"""
        async with self._lock:
            now = datetime.now()
            
            # 清理过期的晋升股票
            expired_codes = [
                code for code, anomaly in self.promoted_stocks.items()
                if anomaly.expire_at < now
            ]
            for code in expired_codes:
                del self.promoted_stocks[code]
                logger.info(f"移除过期晋升股票: {code}")
            
            # 清理过期的手动股票
            expired_manual = [
                code for code, expire_at in self.manual_stocks.items()
                if expire_at < now
            ]
            for code in expired_manual:
                del self.manual_stocks[code]
                logger.info(f"移除过期手动股票: {code}")
    
    async def get_all_dynamic_stocks(self) -> List[str]:
        """获取所有动态股票（晋升 + 手动）"""
        async with self._lock:
            promoted = list(self.promoted_stocks.keys())
            manual = list(self.manual_stocks.keys())
            # 合并去重
            return list(set(promoted + manual))
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "promoted_count": len(self.promoted_stocks),
            "manual_count": len(self.manual_stocks),
            "total_dynamic": len(self.promoted_stocks) + len(self.manual_stocks),
            "max_capacity": self.max_dynamic_size
        }
```

### 3. 集成到采集调度器

```python
# src/scheduler/acquisition_scheduler.py
class AcquisitionScheduler:
    def __init__(self):
        # ... 原有代码 ...
        self.anomaly_detector = AnomalyDetector()
        self.dynamic_manager = DynamicPoolManager(max_dynamic_size=10)
    
    async def _run_acquisition_round(self):
        """执行一轮采集"""
        # 1. 获取L1核心池
        core_pool = await self.pool_switcher.get_current_pool()
        
        # 2. 获取动态池
        dynamic_pool = await self.dynamic_manager.get_all_dynamic_stocks()
        
        # 3. 合并（动态池优先，确保被采集）
        full_pool = list(set(dynamic_pool + core_pool))
        
        logger.info(f"本轮采集: 核心池 {len(core_pool)}, 动态池 {len(dynamic_pool)}, 合计 {len(full_pool)}")
        
        # 4. 批量采集
        data = await self._fetch_all_stocks(full_pool)
        
        # 5. 异动检测（仅对核心池外的股票）
        other_stocks_data = self._filter_non_core(data, core_pool)
        anomalies = await self.anomaly_detector.detect_anomalies(other_stocks_data)
        
        # 6. 晋升异动股票
        for anomaly in anomalies:
            await self.dynamic_manager.promote(anomaly)
        
        # 7. 清理过期股票
        await self.dynamic_manager.cleanup_expired()
        
        # 8. 保存数据
        await self._save_data(data)
```

---

## ✅ 测试计划

### 1. 单元测试

```python
# tests/test_anomaly_detector.py
@pytest.mark.asyncio
async def test_detect_price_change_anomaly():
    """测试涨幅异动检测"""
    detector = AnomalyDetector(price_change_threshold=3.0)
    
    # 模拟价格数据
    data = pd.DataFrame([
        {"代码": "000001", "名称": "平安银行", "最新价": 10.3, "涨跌幅": 5.0}
    ])
    
    anomalies = await detector.detect_anomalies(data)
    assert len(anomalies) == 1
    assert anomalies[0].trigger_reason == "涨幅"

@pytest.mark.asyncio
async def test_dynamic_pool_promotion():
    """测试动态池晋升"""
    manager = DynamicPoolManager(max_dynamic_size=2)
    
    anomaly1 = AnomalyStock(
        code="000001", name="test1", trigger_reason="涨幅",
        trigger_value=5.0, detected_at=datetime.now(),
        expire_at=datetime.now() + timedelta(minutes=30)
    )
    
    await manager.promote(anomaly1)
    assert len(manager.promoted_stocks) == 1
```

---

## 📊 监控指标

- **晋升次数/天**: 记录每天触发的异动次数
- **晋升股票数量**: 当前动态池大小
- **平均持续时间**: 股票在动态池的平均停留时间
- **捕获成功率**: 晋升股票中真正持续异动的比例

---

## 🚀 API接口（手动操作）

```python
# src/api/routers/stock_pool.py
from fastapi import APIRouter

router = APIRouter(prefix="/stock-pool", tags=["Stock Pool"])

@router.post("/manual-add")
async def add_manual_stock(code: str, duration: int = 60):
    """手动添加股票到监控池"""
    await dynamic_manager.add_manual(code, duration)
    return {"message": f"已添加 {code}, 持续 {duration} 分钟"}

@router.delete("/manual-remove/{code}")
async def remove_manual_stock(code: str):
    """移除手动添加的股票"""
    await dynamic_manager.remove_manual(code)
    return {"message": f"已移除 {code}"}

@router.get("/dynamic-stats")
async def get_dynamic_stats():
    """获取动态池统计"""
    return dynamic_manager.get_stats()
```

---

## 📝 注意事项

1. **误报控制**: 涨幅3%的阈值可能较低，初期可调高到5%观察
2. **时区问题**: 所有时间戳使用 `Asia/Shanghai`
3. **并发安全**: 动态池操作必须使用锁保护
4. **内存管理**: 价格历史只保留5分钟，定期清理

---

**创建时间**: 2025-12-01  
**创建人**: AI 系统架构师  
**审核人**: 待定
