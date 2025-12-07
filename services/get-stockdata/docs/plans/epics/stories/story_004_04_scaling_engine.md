# Story 004.04: 智能扩容系统

**Epic**: EPIC-004 股票池动态管理  
**优先级**: P1  
**预估工期**: 2 天  
**状态**: 📝 待开始  
**前置依赖**: Story 004.01, EPIC-005 (监控体系)

---

## 📋 Story 描述

**作为** 系统架构师  
**我希望** 系统能基于监控指标自动建议或执行股票池扩容  
**以便** 在资源充足时逐步提升市场覆盖率

---

## 🎯 验收标准

### 功能需求
- [ ] 实现扩容路径：100 → 150 → 200 → 300 → 500 → 800 只
- [ ] 扩容条件监控：QPS < 0.8 && 成功率 > 99% && CPU < 60%
- [ ] 每次扩容增加 50-100 只股票
- [ ] 扩容前自动发送告警通知，支持人工审批

### 监控需求
- [ ] 实时监控系统QPS、成功率、CPU/内存使用率
- [ ] 连续3天满足扩容条件时触发建议
- [ ] 扩容执行后监控7天，确保稳定

### 测试需求
- [ ] 单元测试覆盖扩容决策逻辑
- [ ] 模拟负载测试验证阈值
- [ ] 回滚机制测试

---

## 🔧 技术设计

### 1. 扩容路径配置

```yaml
# config/scaling_strategy.yaml
version: "1.0.0"

# 扩容路径
scaling_path:
  - level: 1
    pool_size: 100
    description: "初始验证阶段"
    min_stable_days: 7
    
  - level: 2
    pool_size: 150
    description: "小幅扩容"
    min_stable_days: 5
    
  - level: 3
    pool_size: 200
    description: "中等规模"
    min_stable_days: 5
    
  - level: 4
    pool_size: 300
    description: "大规模采集"
    min_stable_days: 7
    
  - level: 5
    pool_size: 500
    description: "全市场核心"
    min_stable_days: 7
    
  - level: 6
    pool_size: 800
    description: "终极目标"
    min_stable_days: 0

# 扩容条件（所有条件必须同时满足）
scaling_conditions:
  qps_threshold: 0.8          # QPS上限使用率 < 80%
  success_rate_threshold: 99.0  # 成功率 > 99%
  cpu_threshold: 60            # CPU使用率 < 60%
  memory_threshold: 70         # 内存使用率 < 70%
  stable_days_required: 3      # 连续稳定天数
  
# 回滚条件（任一条件满足即回滚）
rollback_conditions:
  success_rate_low: 95.0       # 成功率 < 95%
  cpu_high: 80                 # CPU > 80%
  memory_high: 85              # 内存 > 85%
  qps_high: 0.95              # QPS使用率 > 95%
```

### 2. 系统指标收集器

```python
# src/monitoring/system_metrics_collector.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List
import psutil

@dataclass
class SystemMetrics:
    """系统指标快照"""
    timestamp: datetime
    qps: float
    success_rate: float
    cpu_percent: float
    memory_percent: float
    pool_size: int

class SystemMetricsCollector:
    """系统指标收集器"""
    
    def __init__(self, max_history_days: int = 7):
        self.max_history_days = max_history_days
        self.metrics_history: List[SystemMetrics] = []
        self._lock = asyncio.Lock()
    
    async def collect(self, scheduler_stats: dict) -> SystemMetrics:
        """收集当前系统指标"""
        # 1. 获取调度器统计
        qps = scheduler_stats.get("current_qps", 0)
        success_rate = scheduler_stats.get("success_rate", 100.0)
        pool_size = scheduler_stats.get("pool_size", 0)
        
        # 2. 获取系统资源
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        
        # 3. 创建快照
        metrics = SystemMetrics(
            timestamp=datetime.now(),
            qps=qps,
            success_rate=success_rate,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            pool_size=pool_size
        )
        
        # 4. 保存到历史
        async with self._lock:
            self.metrics_history.append(metrics)
            
            # 清理过期数据
            cutoff = datetime.now() - timedelta(days=self.max_history_days)
            self.metrics_history = [
                m for m in self.metrics_history 
                if m.timestamp > cutoff
            ]
        
        return metrics
    
    async def get_avg_metrics(self, days: int) -> dict:
        """获取最近N天的平均指标"""
        async with self._lock:
            cutoff = datetime.now() - timedelta(days=days)
            recent = [m for m in self.metrics_history if m.timestamp > cutoff]
            
            if not recent:
                return None
            
            return {
                "avg_qps": sum(m.qps for m in recent) / len(recent),
                "avg_success_rate": sum(m.success_rate for m in recent) / len(recent),
                "avg_cpu": sum(m.cpu_percent for m in recent) / len(recent),
                "avg_memory": sum(m.memory_percent for m in recent) / len(recent),
                "sample_count": len(recent)
            }
```

### 3. 扩容决策引擎

```python
# src/services/stock_pool/scaling_engine.py
from enum import Enum

class ScalingDecision(Enum):
    MAINTAIN = "maintain"      # 保持当前规模
    SCALE_UP = "scale_up"      # 建议扩容
    ROLLBACK = "rollback"      # 建议回滚

class ScalingEngine:
    """扩容决策引擎"""
    
    def __init__(self, config_path: str = "config/scaling_strategy.yaml"):
        self.config = self._load_config(config_path)
        self.current_level = 1
        self.last_scaling_date: Optional[datetime] = None
        self.approval_pending = False
    
    def _load_config(self, path: str) -> dict:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    
    async def evaluate(self, 
                       metrics_collector: SystemMetricsCollector,
                       current_pool_size: int) -> ScalingDecision:
        """评估是否应该扩容"""
        
        # 1. 确定当前等级
        self._update_current_level(current_pool_size)
        
        # 2. 检查是否需要回滚
        if await self._should_rollback(metrics_collector):
            return ScalingDecision.ROLLBACK
        
        # 3. 检查是否满足扩容条件
        if await self._should_scale_up(metrics_collector):
            return ScalingDecision.SCALE_UP
        
        return ScalingDecision.MAINTAIN
    
    def _update_current_level(self, pool_size: int):
        """根据当前池大小更新等级"""
        for level in self.config["scaling_path"]:
            if pool_size <= level["pool_size"]:
                self.current_level = level["level"]
                break
    
    async def _should_rollback(self, 
                               metrics_collector: SystemMetricsCollector) -> bool:
        """判断是否需要回滚"""
        # 获取最近1天的平均指标
        avg = await metrics_collector.get_avg_metrics(days=1)
        if not avg:
            return False
        
        conditions = self.config["rollback_conditions"]
        
        # 任一条件满足即回滚
        if avg["avg_success_rate"] < conditions["success_rate_low"]:
            logger.warning(f"成功率过低: {avg['avg_success_rate']:.2f}%")
            return True
        
        if avg["avg_cpu"] > conditions["cpu_high"]:
            logger.warning(f"CPU过高: {avg['avg_cpu']:.2f}%")
            return True
        
        if avg["avg_memory"] > conditions["memory_high"]:
            logger.warning(f"内存过高: {avg['avg_memory']:.2f}%")
            return True
        
        # 注意：这里需要获取QPS上限，暂时硬编码为1.3
        qps_limit = 1.3
        if avg["avg_qps"] / qps_limit > conditions["qps_high"]:
            logger.warning(f"QPS过高: {avg['avg_qps']:.2f}")
            return True
        
        return False
    
    async def _should_scale_up(self, 
                               metrics_collector: SystemMetricsCollector) -> bool:
        """判断是否满足扩容条件"""
        # 1. 检查是否已达最大等级
        if self.current_level >= len(self.config["scaling_path"]):
            return False
        
        # 2. 检查是否在等待审批
        if self.approval_pending:
            return False
        
        # 3. 获取当前等级配置
        current_config = self.config["scaling_path"][self.current_level - 1]
        stable_days = current_config["min_stable_days"]
        
        # 4. 获取最近N天的平均指标
        avg = await metrics_collector.get_avg_metrics(days=stable_days)
        if not avg:
            logger.info(f"数据不足，需要至少 {stable_days} 天的稳定运行")
            return False
        
        # 5. 检查所有扩容条件
        conditions = self.config["scaling_conditions"]
        qps_limit = 1.3
        
        checks = {
            "QPS使用率": avg["avg_qps"] / qps_limit < conditions["qps_threshold"],
            "成功率": avg["avg_success_rate"] > conditions["success_rate_threshold"],
            "CPU使用率": avg["avg_cpu"] < conditions["cpu_threshold"],
            "内存使用率": avg["avg_memory"] < conditions["memory_threshold"]
        }
        
        # 6. 打印检查结果
        for name, passed in checks.items():
            status = "✓" if passed else "✗"
            logger.info(f"{status} {name}")
        
        # 7. 所有条件必须满足
        return all(checks.values())
    
    def get_next_level_info(self) -> dict:
        """获取下一级别的信息"""
        if self.current_level >= len(self.config["scaling_path"]):
            return None
        
        return self.config["scaling_path"][self.current_level]
    
    async def execute_scaling(self, pool_manager) -> bool:
        """执行扩容操作"""
        try:
            next_level = self.get_next_level_info()
            if not next_level:
                logger.warning("已达最大等级，无法扩容")
                return False
            
            target_size = next_level["pool_size"]
            current_size = len(await pool_manager.get_current_pool())
            
            logger.info(f"执行扩容: {current_size} -> {target_size}")
            
            # 扩容逻辑：补充沪深300的下一批股票
            additional_stocks = await self._get_additional_stocks(
                current_size, 
                target_size
            )
            
            await pool_manager.expand_pool(additional_stocks)
            
            self.current_level += 1
            self.last_scaling_date = datetime.now()
            self.approval_pending = False
            
            logger.info(f"扩容完成，当前等级: {self.current_level}")
            return True
            
        except Exception as e:
            logger.error(f"扩容失败: {e}")
            return False
    
    async def _get_additional_stocks(self, 
                                    current_size: int, 
                                    target_size: int) -> List[str]:
        """获取需要补充的股票"""
        # 从沪深300 + 中证500中选取
        df = ak.index_stock_cons(symbol="000300")  # 沪深300
        df2 = ak.index_stock_cons(symbol="000905")  # 中证500
        
        all_stocks = pd.concat([df, df2])
        
        # 已有股票跳过
        # 按成交额排序，取需要的数量
        additional_count = target_size - current_size
        return all_stocks.head(target_size).tail(additional_count)["品种代码"].tolist()
```

---

## ✅ 测试计划

### 1. 单元测试

```python
# tests/test_scaling_engine.py
@pytest.mark.asyncio
async def test_scaling_decision_when_stable():
    """测试稳定时的扩容决策"""
    engine = ScalingEngine()
    collector = SystemMetricsCollector()
    
    # 模拟7天稳定数据
    for _ in range(7):
        await collector.collect({
            "current_qps": 0.5,
            "success_rate": 99.5,
            "pool_size": 100
        })
    
    decision = await engine.evaluate(collector, 100)
    assert decision == ScalingDecision.SCALE_UP
```

---

## 📊 监控与通知

```python
# 扩容建议通知
async def notify_scaling_suggestion():
    message = f"""
    📈 股票池扩容建议
    
    当前等级: Level {engine.current_level}
    当前规模: {current_size} 只
    建议扩容至: {next_level['pool_size']} 只
    
    系统指标（最近3天平均）:
    - QPS使用率: {avg['avg_qps']/1.3*100:.1f}%
    - 成功率: {avg['avg_success_rate']:.2f}%
    - CPU使用率: {avg['avg_cpu']:.1f}%
    - 内存使用率: {avg['avg_memory']:.1f}%
    
    请审批后执行扩容
    """
    
    # 发送钉钉/邮件通知
    await send_alert(message)
```

---

## 📝 注意事项

1. **人工审批**: 初期建议人工审批，避免自动扩容带来风险
2. **回滚预案**: 扩容后如发现问题，需立即回滚
3. **增量验证**: 每次扩容只增加50-100只，逐步验证
4. **监控窗口**: 扩容后监控7天，确保稳定再进行下一次

---

**创建时间**: 2025-12-01  
**创建人**: AI 系统架构师  
**审核人**: 待定
