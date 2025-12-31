# 数据质量全生命周期管理

## 核心策略

**个股数据有任何问题 → 清除 → 重新采集 → 重新同步**

不做局部修补，只做全量重建。

---

## 一、数据流向

```
Baostock/AkShare/Mootdx  ← 一级源
           ↓ 采集
        MySQL            ← 二级源
           ↓ 同步(含验证)
      ClickHouse         ← 目标库
           ↓ 定期检测
      质量检查服务
           ↓ 发现问题
      触发重建
```

---

## 二、验证层（写入时拦截）

### 2.1 验证规则

| 层级 | 检查内容 | 失败处理 |
|:----|:--------|:--------|
| L1 | 必填字段、价格范围 | 跳过该条 |
| L5 | OHLC一致性 | 跳过该条 |
| L7 | 批次去重 | 自动去重 |

### 2.2 阈值保护

```python
if fail_rate > 0.2:
    raise ValueError("验证失败率过高，任务终止")
```

**触发后续操作**: 人工排查 → 修复数据源或调整规则 → 重新同步

---

## 三、检测层（定期发现）

### 3.1 检测频率

| 检测项 | 频率 | API |
|:------|:----|:----|
| 时效性 | 每日 20:00 | `/quality/timeliness` |
| 日完整性 | 每日 20:00 | `/quality/daily-completeness` |
| 重复数据 | 每日 20:00 | `/quality/duplicates` |
| 个股完整性 | 每周 | `/quality/stock/{code}` |

### 3.2 问题判定

| 问题类型 | 判定标准 |
|:--------|:--------|
| 数据滞后 | 最新日期 > 1天 (非周末) |
| 日缺失 | 当日股票数 < 前日 95% |
| 个股缺失 | 缺失交易日 > 5% |
| 重复 | duplicate_count > 0 |

---

## 四、修复层（全量重建）

### 4.1 修复策略

**唯一策略**: 清除 → 调用采集服务 → 同步

```bash
# 个股全量重建
POST /api/v1/repair/stock/{stock_code}
```

### 4.2 重建流程

```
Step 1: 清除 ClickHouse 该股票数据
        ALTER TABLE stock_kline_daily DELETE 
        WHERE stock_code = 'sh.600519';

Step 2: 调用远程采集服务 API (触发重新采集)
        POST http://{采集服务地址}/api/v1/collect/stock_history
        Body: {"stock_code": "sh.600519", "start_date": "1990-01-01"}
        
        (采集服务负责: Baostock/AkShare → MySQL)

Step 3: 等待采集完成 (轮询或回调)

Step 4: 从 MySQL 同步到 ClickHouse
        调用本地同步接口
```

### 4.3 服务职责划分

| 服务 | 职责 |
|:----|:----|
| **采集服务** (远程) | Baostock/AkShare → MySQL |
| **get-stockdata** (本地) | MySQL → ClickHouse + 质量检测 |

### 4.4 重建 API 实现逻辑

```python
async def repair_stock(stock_code: str):
    # 1. 清除 ClickHouse
    await clickhouse.execute(
        "ALTER TABLE stock_kline_daily DELETE WHERE stock_code = %s",
        stock_code
    )
    
    # 2. 调用远程采集服务
    response = await http_client.post(
        f"{COLLECT_SERVICE_URL}/api/v1/collect/stock_history",
        json={"stock_code": stock_code}
    )
    
    # 3. 等待采集完成
    if response["status"] == "accepted":
        # 异步任务，返回任务ID，后续轮询或等待回调
        return {"status": "collecting", "task_id": response["task_id"]}
    
    # 4. 采集完成后触发同步
    # (可以由采集服务回调触发，或定时同步自动处理)
```

### 4.3 触发条件

| 触发场景 | 自动/手动 |
|:--------|:---------|
| 质量检查发现缺失>5% | 人工确认后手动 |
| 验证失败率>20% | 人工排查后手动 |
| 用户反馈数据错误 | 手动 |
| 重复数据 | 手动清理 |

---

## 五、完整流程图

```
┌─────────────┐
│ 数据采集    │ ← Baostock/AkShare
└──────┬──────┘
       ↓
┌─────────────┐
│ 写入 MySQL  │
└──────┬──────┘
       ↓
┌─────────────┐     失败率>20%     ┌─────────────┐
│ 验证层检查  │ ──────────────────→ │ 任务失败    │
│ (L1/L5/L7) │                     │ 人工排查    │
└──────┬──────┘                     └──────┬──────┘
       ↓ 通过                              ↓
┌─────────────┐                     ┌─────────────┐
│ 写入        │                     │ 修复源数据  │
│ ClickHouse  │                     │ 或调整规则  │
└──────┬──────┘                     └──────┬──────┘
       ↓                                   ↓
┌─────────────┐                     ┌─────────────┐
│ 每日质量    │                     │ 重新同步    │
│ 检查        │                     └─────────────┘
└──────┬──────┘
       ↓ 发现问题
┌─────────────┐
│ 定位问题    │
│ 股票/日期   │
└──────┬──────┘
       ↓
┌─────────────┐
│ 个股全量    │ → 清除 → 采集 → 同步
│ 重建        │
└─────────────┘
```

---

## 六、API 清单

| 类别 | API | 说明 |
|:----|:----|:----|
| **检测** | `GET /quality/timeliness` | 时效性检查 |
| **检测** | `GET /quality/daily-completeness` | 日完整性 |
| **检测** | `GET /quality/stock/{code}` | 个股质量 |
| **检测** | `GET /quality/report/daily` | 日报 |
| **修复** | `POST /repair/stock/{code}` | 个股重建 |
| **同步** | `POST /sync/kline` | K线同步 |

---

## 七、核心原则

1. **不做局部修补**: 有问题就重建，不搞复杂的差分修复
2. **从源头重建**: 清除所有层级数据，从原始数据源重新开始
3. **人工确认**: 重建操作需人工触发，避免误操作
4. **保持简单**: 一个策略解决所有问题
