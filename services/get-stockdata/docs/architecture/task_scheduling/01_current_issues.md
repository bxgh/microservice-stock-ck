# 当前问题分析

## 已识别的 7 类风险

### 🔴 P0 - 高风险

#### 1. 无限循环无守护

**位置**: `snapshot_recorder.py`

```python
while self.is_running:
    if not self.scheduler.should_run_now():
        await self.scheduler.wait_for_next_run()  # 可能 sleep 数小时
```

**问题**：进程被 Kill 后无人知道，快照数据静默丢失

---

#### 2. BackgroundTasks 执行无追踪

**位置**: `sync_routes.py`, `repair_routes.py`

```python
background_tasks.add_task(_run_sync_task, request, redis)
```

**问题**：任务失败无告警，无法追溯执行历史

---

### 🟡 P1 - 中风险

#### 3. 交易日历判断分散

**问题**：只有 get-stockdata 使用 CalendarService，其他服务无感知

---

#### 4. 连接池预热失败无熔断

**位置**: `scheduler.py`

```python
try:
    await connection_monitor.warmup_all()
except Exception as e:
    self.logger.warning(f"Failed to warmup: {e}")  # 只是 warning
```

**问题**：预热失败仍会启动采集，导致开盘首分钟失败

---

### 🟢 P2 - 低风险

#### 5. 任务状态查询能力缺失

**位置**: `repair_routes.py`

```python
async def get_rebuild_status(stock_code: str):
    return {"status": "not_implemented"}
```

---

#### 6. 重复 Nacos 心跳模板代码

5 个服务有几乎相同的 `nacos_registry_simple.py`

---

#### 7. InternalLooper 边界模糊

虽有规范，但无强制检查防止滥用

---

## 核心痛点总结

| 排名 | 痛点 | 根因 |
|:-----|:-----|:-----|
| 1 | 任务失败无人知道 | BackgroundTasks + 无持久化 + 无告警 |
| 2 | 休眠与死亡无法区分 | asyncio.sleep + 无细粒度健康检查 |
