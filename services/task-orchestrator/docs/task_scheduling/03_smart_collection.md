# 智能采集框架

## 核心理念

**零人工干预、自感知、自恢复、自验证**

## 状态机

```
IDLE → COLLECTING → SYNCING → VALIDATING → SUCCESS
                                    ↓
                               INCOMPLETE
                                    ↓
                               REPAIRING → 回到 VALIDATING
```

## 五大智能能力

### 1. 智能感知 (Awareness)

| 感知项 | 检测方式 | 触发动作 |
|:-------|:---------|:---------|
| 是否交易日 | CalendarService | 非交易日跳过 |
| 数据源健康 | 前置 ping | 选择可用源 |
| 上次结果 | 查 sync_logs | 决定增量/全量 |

### 2. 智能路由 (Routing)

```python
async def get_best_source(stock_code):
    sources = [Baostock, AkShare, Mootdx]
    healthy = [s for s in sources if await s.ping()]
    return sorted(healthy, key=lambda s: s.success_rate)[-1]
```

### 3. 智能重试 (Self-Healing)

| 错误类型 | 策略 |
|:---------|:-----|
| 网络错误 | 30s 后重试，最多 3 次 |
| 超时 | 60s 后重试，最多 2 次 |
| 数据源宕机 | 切换备用源 |
| 部分失败 | 继续剩余 |

### 4. 智能验证 (Validation)

```python
async def auto_validate(date):
    checks = await asyncio.gather(
        check_record_count(date),      # 记录数 >= 4500
        check_date_coverage(date),      # 日期连续
        check_ohlc_integrity(date),     # OHLC 完整
    )
    return all(checks)
```

### 5. 智能修复 (Repair)

```python
async def auto_repair(failed_stocks):
    for stock in failed_stocks:
        for source in [AkShare, Mootdx, Baostock]:
            try:
                data = await source.fetch(stock)
                await save(data)
                break
            except:
                continue
```

## 成功判定标准

| 检查项 | 标准 |
|:-------|:-----|
| 记录数完整 | ≥ 预期股票数 × 95% |
| 日期完整 | 最大日期 = 最新交易日 |
| 质量合格 | 校验失败率 < 1% |
