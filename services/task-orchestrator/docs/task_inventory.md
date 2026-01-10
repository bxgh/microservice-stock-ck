# 现有任务调度清单与迁移建议

**日期**: 2026-01-02

---

## 1. 现有调度机制总览

| 服务 | 调度器 | 用途 | 迁移优先级 |
|:-----|:-------|:-----|:-----------|
| **task-orchestrator** | APScheduler | 集中调度 | N/A (控制中心) |
| **get-stockdata** | AcquisitionScheduler | 交易时段控制 | P1 (需废弃) |
| **quant-strategy** | InternalLooper | 轻量维护任务 | P3 (保留本地) |

---

## 2. 详细任务清单

### 2.1 task-orchestrator (已实现)

**任务**: 
- 每日K线同步 + 质量检查 (17:30)
- 盘后分笔采集 Shard-0 (16:35)
- 每日股票代码采集 (09:05)

**状态**: ✅ 已实现


---

### 2.2 get-stockdata

#### AcquisitionScheduler

**位置**: `src/core/scheduling/scheduler.py`

**功能**:
- 判断交易时段 (09:10-11:35, 12:55-15:10)
- 自动休眠/唤醒

**问题**:
- ❌ 包含 `asyncio.sleep` 自循环
- ❌ 未被实际使用
- ❌ 违反"单一调度源"原则

**迁移建议**: 废弃

---

### 2.3 quant-strategy

#### InternalLooper

**位置**: `src/core/looper.py`

**用途**: 秒级轻量任务
```python
- 缓存刷新 (60s)
- 心跳发送 (30s)
- 临时清理 (300s)
```

**迁移建议**: ❌ 不迁移 (保留本地)

---

## 3. 潜在可迁移的任务

### 数据采集
- ✅ K线同步 (已迁移)
- ⚠️ 财务数据更新 (待新增)
- ⚠️ 估值数据更新 (待新增)

### 策略任务
- ⚠️ 每日全市场扫描 (待新增)
- ⚠️ 策略参数优化 (待新增)

### 系统维护
- ⚠️ 数据库备份 (待新增)
- ⚠️ 日志清理 (待新增)
- ⚠️ 缓存预热 (待新增)

---

## 4. YAML 配置示例

### 建议创建: `services/task-orchestrator/config/tasks.yml`

```yaml
version: "1.0"
timezone: "Asia/Shanghai"

tasks:
  # K线同步 (已实现)
  - id: daily_kline_sync
    name: K线每日同步
    schedule:
      type: trading_cron
      expression: "5 15 * * 1-5"
    enabled: true
  
  # 待新增: 策略扫描
  - id: daily_strategy_scan
    name: 每日策略扫描
    schedule:
      type: trading_cron
      expression: "30 18 * * 1-5"
    target:
      image: quant-strategy:latest
      command: ["jobs.daily_scan"]
    dependencies: [daily_kline_sync]
  
  # 待新增: 数据库备份
  - id: db_backup
    name: 数据库备份
    schedule:
      type: cron
      expression: "0 3 * * *"
    target:
      image: gsd-worker:latest
      command: ["jobs.db_backup"]
```

---

## 5. 废弃计划

**AcquisitionScheduler**  
位置: `services/get-stockdata/src/core/scheduling/scheduler.py`

**原因**:
- 包含自循环
- 未被使用
- 违反架构原则

**步骤**:
1. 确认无调用
2. 删除 scheduler.py
3. 更新文档

---

## 6. 总结

### 迁移优先级

**P1** (立即):
- ✅ K线同步 (已完成)
- ⚠️ 每日策略扫描 (待实现)
- ⚠️ 数据库备份 (待实现)

**P2** (一周内):
- 财务数据更新
- 缓存预热
- 日志清理

**P3** (可选):
- 估值数据更新
- 策略参数优化

### 下一步

1. 创建 `config/tasks.yml`
2. 实现 YAML 加载
3. 添加新任务
4. 废弃 AcquisitionScheduler
