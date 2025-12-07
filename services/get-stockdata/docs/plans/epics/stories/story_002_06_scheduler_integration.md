# Story 002-06: 连接池与调度器集成

**Story ID**: STORY-002-06  
**Epic**: EPIC-002 高可用采集引擎  
**优先级**: P2  
**估算**: 1 天  
**状态**: ✅ 已完成  
**依赖**: Story 4, Story 5  
**实际完成时间**: 2025-11-29

---

## 📋 Story 概述

将连接池管理与采集调度器集成，实现基于交易时间的智能资源管理。在交易时段开始前自动预热连接池，在交易结束后自动释放连接，以达到性能与资源消耗的最佳平衡。

### 业务价值
- **降低延迟**: 盘前预热确保开盘第一秒即可高速采集
- **节省资源**: 盘后自动释放连接，减少服务器负载和被封禁风险
- **自动化运维**: 无需人工干预连接的建立与释放

---

## 🎯 验收标准

### 功能验收
- [ ] `ConnectionMonitor` 支持 `warmup_all()` 和 `cooldown_all()` 方法
- [ ] `AcquisitionScheduler` 在唤醒时自动触发预热
- [ ] `AcquisitionScheduler` 在休眠前自动触发冷却
- [ ] 系统日志清晰记录连接池的状态变更

### 场景验证
- **场景 1 (预热)**: 模拟时间到达 09:10，系统唤醒，所有注册的数据源建立连接。
- **场景 2 (冷却)**: 模拟时间到达 15:10，系统休眠，所有注册的数据源释放连接。

---

## 🏗️ 技术设计

### 1. 扩展 ConnectionMonitor

在 `src/core/monitoring/connection_monitor.py` 中添加：

```python
    async def warmup_all(self):
        """预热所有连接池"""
        logger.info("🔥 Warming up all connection pools...")
        for name, manager in self._managers.items():
            try:
                await manager.initialize()
                logger.info(f"  ✅ {name} initialized")
            except Exception as e:
                logger.error(f"  ❌ {name} warmup failed: {e}")

    async def cooldown_all(self):
        """冷却所有连接池"""
        logger.info("❄️ Cooling down all connection pools...")
        for name, manager in self._managers.items():
            try:
                await manager.cleanup()
                logger.info(f"  ✅ {name} cleaned up")
            except Exception as e:
                logger.error(f"  ❌ {name} cooldown failed: {e}")
```

### 2. 修改 AcquisitionScheduler

在 `src/core/scheduling/scheduler.py` 中：

1.  引入 `connection_monitor`。
2.  在 `wait_for_next_run` 中添加钩子。

```python
    async def wait_for_next_run(self):
        # ... 计算等待时间 ...
        
        if wait_seconds > 0:
            # 进入休眠前 -> 冷却
            self.state = SystemState.SLEEPING
            await connection_monitor.cooldown_all()  # 新增
            
            await asyncio.sleep(wait_seconds)
            
            # 唤醒后 -> 预热
            self.state = SystemState.RUNNING
            await connection_monitor.warmup_all()    # 新增
```

---

## 📅 实施计划

### 步骤 1: 扩展 ConnectionMonitor
添加预热和冷却方法。

### 步骤 2: 集成 Scheduler
修改调度器逻辑，调用监控器方法。

### 步骤 3: 测试验证
编写测试模拟时间流逝，验证方法被调用。

---

**文档版本**: v1.0  
**创建时间**: 2025-11-29  
**预计完成时间**: 2025-11-29
