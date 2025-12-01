# EPIC-002: 高可用采集引擎 - User Stories

**Epic ID**: EPIC-002  
**优先级**: P0  
**预估工期**: 2 周  
**状态**: 规划中

---

## 📋 Epic 概述

构建稳定可靠的数据采集引擎，具备故障自愈和弹性处理能力。本 Epic 包含两大核心方向：
1. **连接管理优化**：提升连接复用效率和稳定性
2. **容错机制**：增加智能重试、熔断和降级能力

---

## 🔍 当前状态分析

### 现有实现问题
1. **MootdxConnection**: 每次创建新连接，无复用机制
2. **TongDaXinClient**: 有基础连接池，但实现较简单
3. **数据源工厂**: TongDaXinDataSource 被禁用，无法使用
4. **无容错机制**: 网络抖动时直接失败，无重试
5. **接口不统一**: 两种数据源连接管理方式完全不同

### 真实代码结构
```
services/get-stockdata/src/
├── data_sources/mootdx/connection.py  # 单连接，无池化
├── services/tongdaxin_client.py     # 有基础连接池
├── data_sources/factory.py         # TongDaXin被注释禁用
└── core/recorder/snapshot_recorder.py  # 直接调用 Mootdx，无重试
```

---

## 📚 User Stories

### 🔴 高优先级 (P0) - 立即实施

---

#### **Story 1: 智能重试与熔断机制**
**状态**: ✅ 已完成 (2025-11-28)

#### **Story 2: Mootdx 连接复用优化**
**状态**: ✅ 已完成 (2025-11-29)

#### **Story 3: 修复 TongDaXin 数据源集成**
**状态**: ✅ 已完成 (2025-11-29)


---

#### **Story 4: 统一数据源连接接口**
**状态**: ✅ 已完成 (2025-11-29)

### 🟢 低优先级 (P2) - 可选优化

---

#### **Story 5: 连接状态监控**
**状态**: ✅ 已完成 (2025-11-29)
**估算**: 1 天  
**依赖**: Story 4

**问题描述**:  
无法监控连接池状态，问题排查困难。

**监控指标设计**:

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ConnectionStats:
    """连接统计信息"""
    total_created: int = 0        # 总创建次数
    total_reused: int = 0         # 总复用次数  
    total_closed: int = 0         # 总关闭次数
    total_failed: int = 0         # 总失败次数
    current_active: int = 0       # 当前活跃连接数
    current_idle: int = 0         # 当前空闲连接数
    last_activity: Optional[datetime] = None  # 最后活动时间
    avg_response_time: float = 0.0  # 平均响应时间（秒）
    success_rate: float = 100.0   # 成功率（%）
```

**实施方案**:
1. 每个连接管理器都维护 `ConnectionStats` 实例
2. 在关键操作点（创建、复用、关闭、失败）更新统计
3. 提供 `get_stats()` API 查询
4. 可选：集成到 Prometheus Metrics

**验收标准**:
- [ ] 每个连接管理器都有 `stats` 属性
- [ ] 能通过 `get_stats()` 获取实时统计
- [ ] 统计数据准确（通过测试验证）
- [ ] 可选：Prometheus 格式导出

---

#### **Story 6: 连接池与调度器集成** 🆕
**状态**: ✅ 已完成 (2025-11-29)
**优先级**: P2  
**估算**: 1 天  
**依赖**: Story 4, EPIC-001 (CalendarService)

**业务价值**:  
让连接池感知交易时段，实现智能的资源管理。

**功能需求**:
1. 非交易时段：连接池进入休眠模式（关闭所有连接）
2. 交易时段前（09:05）：连接池预热（提前建立连接）
3. 午休时段：释放部分连接，降低资源占用

**技术方案**:

```python
class SchedulerAwareConnectionManager(ConnectionManagerInterface):
    """支持调度感知的连接管理器"""
    
    def __init__(self, base_manager: ConnectionManagerInterface, scheduler: AcquisitionScheduler):
        self.base_manager = base_manager
        self.scheduler = scheduler
        self._is_preheated = False
    
    async def prewarm(self):
        """预热连接池"""
        if self.scheduler.should_run_now() and not self._is_preheated:
            logger.info("Prewarming connection pool...")
            await self.base_manager.initialize()
            self._is_preheated = True
    
    async def hibernate(self):
        """休眠连接池"""
        if not self.scheduler.should_run_now():
            logger.info("Hibernating connection pool...")
            await self.base_manager.cleanup()
            self._is_preheated = False
```

**验收标准**:
- [x] 实现连接池预热逻辑
- [x] 实现连接池冷却/释放逻辑
- [x] 调度器在正确的时间点触发预热和冷却
- [x] 验证资源释放效果

---

## � 实施路线图

| 阶段 | 任务 | 估算 | 状态 |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Story 1: 智能重试与熔断 | 2 天 | ✅ 完成 |
| **Phase 1** | Story 2: Mootdx 连接复用 | 2 天 | ✅ 完成 |
| **Phase 1** | Story 3: 修复 TongDaXin 集成 | 1 天 | ✅ 完成 |
| **Phase 2** | Story 4: 统一连接接口 | 3 天 | ✅ 完成 |
| **Phase 2** | Story 5: 连接状态监控 | 1 天 | ✅ 完成 |
| **Phase 2** | Story 6: 调度器集成 | 1 天 | ✅ 完成 |

## ✅ 成功标准

1.  **可用性**: 数据采集成功率 > 99.9% (通过重试和熔断保证)
2.  **性能**: 单次采集延迟降低 50% (通过连接复用)
3.  **可维护性**: 新增数据源只需实现统一接口，无需修改核心逻辑
4.  **资源效率**: 非交易时间资源占用降低 90%

---

## 🎯 成功指标

### 技术指标
- **采集成功率**: ≥ 99.8% (从当前 ~95% 提升)
- **连接复用率**: ≥ 90% (减少创建次数)
- **平均响应时间**: ≤ 500ms (95% 分位)
- **异常恢复时间**: ≤ 5 分钟

### 业务指标
- **数据完整性**: ≥ 99.9% (交易时段覆盖度)
- **系统可用性**: ≥ 99.5%
- **人工干预频率**: ≤ 1 次/周

### 质量指标
- **单元测试覆盖率**: ≥ 90%
- **集成测试通过率**: 100%
- **代码质量评分**: ≥ 8.5/10
- **文档完整性**: ≥ 90%

---

## 🔄 风险与应对

### 风险1: TongDaXin 依赖问题复杂
**应对**: 如果修复成本过高，暂时放弃该数据源，专注于 Mootdx 优化

### 风险2: 重试机制导致 QPS 超限
**应对**: 在重试逻辑中增加 QPS 控制，确保总请求频率在安全范围内

### 风险3: 连接池改造影响现有功能
**应对**: 采用包装器模式，不修改原有代码，只在外层增加新功能

---

**文档版本**: v2.0  
**最后更新**: 2025-11-28  
**修订说明**: 根据 EPIC-001 完成情况和架构评审意见，重新组织 Story 优先级，补充智能重试与熔断机制
