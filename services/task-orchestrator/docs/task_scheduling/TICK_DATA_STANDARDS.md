# 📊 分笔数据采集开发规范

> **版本**: 1.0  
> **更新日期**: 2026-01-06  
> **维护者**: AI Agent

---

## 1. 概述

分笔数据（Tick Data）是量化交易系统的核心原材料，记录了每一笔成交的详细信息。本规范定义了分笔数据采集的技术标准、实现规范和最佳实践。

### 1.1 数据定义

| 字段 | 类型 | 说明 |
|------|------|------|
| `stock_code` | String | 股票代码（如 `000001`） |
| `trade_date` | Date | 交易日期 |
| `tick_time` | String | 成交时间（`HH:MM` 或 `HH:MM:SS`） |
| `price` | Decimal(10,3) | 成交价格 |
| `volume` | UInt32 | 成交量（股） |
| `amount` | Decimal(18,2) | 成交额（元） |
| `direction` | UInt8 | 买卖方向：0=买盘, 1=卖盘, 2=中性 |

### 1.2 数据来源

| 来源 | 时效 | 适用场景 |
|------|------|----------|
| **mootdx** | 盘后 T+0 | 主数据源，获取当日历史分笔 |
| ~~实时行情~~ | 盘中 | 暂不支持，未来扩展 |

---

## 2. 核心技术规范

### 2.1 采集时机

| 时段 | 状态 | 说明 |
|------|------|------|
| 09:25 | ✅ 必须采集 | 集合竞价成交，极其重要 |
| 09:30-11:30 | ✅ 采集 | 上午连续竞价 |
| 11:30-13:00 | ⛔ 无数据 | 午间休市 |
| 13:00-14:57 | ✅ 采集 | 下午连续竞价 |
| 14:57-15:00 | ✅ 采集 | 尾盘集合竞价 |
| 15:00 后 | ⏰ 采集窗口 | 盘后采集任务执行时间 |

### 2.2 智能搜索矩阵策略

> **问题**: mootdx 的分笔数据 API 需要指定 `start` 和 `offset` 参数，但 09:25 集合竞价数据位置不固定。

**解决方案**: 使用**搜索矩阵**策略，遍历多个 (start, offset) 组合直到找到目标数据。

```python
SEARCH_MATRIX = [
    # 优先级从高到低
    (3500, 800, "万科A前区域"),
    (4000, 500, "万科A原成功"),
    (3000, 500, "扩展前区"),
    (2500, 500, "更早区域"),
    (2000, 500, "再早区域"),
    (0, 500, "从头开始"),     # 兜底策略
]
```

**算法逻辑**:
1. 遍历矩阵，逐个尝试 (start, offset) 组合
2. 检查返回数据中是否包含 `09:25` 或 `09:30` 时间戳
3. 找到后继续采集 1-2 步，确保数据完整性
4. 合并去重所有批次数据

### 2.3 并发控制

```python
# ⚠️ 关键参数
CONCURRENCY = 3  # 最大并发股票数

# 使用 asyncio.Semaphore 控制
semaphore = asyncio.Semaphore(concurrency)
async with semaphore:
    await sync_stock(code, trade_date)
```

**理由**:
- mootdx 服务器压力敏感
- 过高并发导致连接拒绝或数据不完整
- 保守值 3 已验证稳定

---

## 3. 存储规范

### 3.1 ClickHouse 表结构

```sql
CREATE TABLE IF NOT EXISTS tick_data
(
    stock_code    String,
    trade_date    Date,
    tick_time     String,
    price         Decimal(10, 3),
    volume        UInt32,
    amount        Decimal(18, 2),
    direction     UInt8,
    created_at    DateTime DEFAULT now()
) ENGINE = ReplicatedReplacingMergeTree(...)
PARTITION BY toYYYYMM(trade_date)
ORDER BY (stock_code, trade_date, tick_time, price, volume)
TTL trade_date + INTERVAL 365 DAY;
```

**设计要点**:
- **引擎**: `ReplicatedReplacingMergeTree` 支持去重
- **分区**: 按月分区，便于 TTL 清理
- **排序键**: 包含时间和价格，支持精确查询
- **TTL**: 365 天自动清理历史数据

### 3.2 物化视图

为加速聚合查询，已创建 `tick_daily_stats` 物化视图：

```sql
SELECT
    stock_code,
    trade_date,
    count() as tick_count,
    sumIf(volume, direction = 0) as buy_volume,
    sumIf(volume, direction = 1) as sell_volume,
    ...
FROM tick_data
GROUP BY stock_code, trade_date;
```

---

## 4. 代码规范

### 4.1 服务结构

```
services/gsd-worker/src/
├── core/
│   └── tick_sync_service.py   # 核心服务类
├── jobs/
│   └── sync_tick.py           # 调度入口
└── config/
    └── hs300_stocks.yaml      # 股票池配置
```

### 4.2 类设计

```python
class TickSyncService:
    """分笔数据同步服务"""
    
    async def initialize(self) -> None:
        """初始化连接池（必须调用）"""
        
    async def close(self) -> None:
        """关闭连接池（必须在 finally 中调用）"""
        
    async def fetch_tick_data_smart(
        self, 
        stock_code: str, 
        trade_date: str
    ) -> List[Dict]:
        """智能策略获取分笔数据"""
        
    async def sync_stock(
        self, 
        stock_code: str, 
        trade_date: str
    ) -> int:
        """同步单只股票，返回写入记录数"""
        
    async def sync_stocks(
        self, 
        stock_codes: List[str],
        trade_date: Optional[str] = None,
        concurrency: int = 3
    ) -> Dict[str, Any]:
        """批量同步，返回统计结果"""
        
    async def get_stock_pool(self) -> List[str]:
        """获取待采集股票池（默认 HS300）"""
```

### 4.3 错误处理

```python
# ✅ 正确：捕获并记录，不中断整体流程
async def sync_stock(self, code: str, date: str) -> int:
    try:
        data = await self.fetch_tick_data_smart(code, date)
        if not data:
            logger.warning(f"{code} 无分笔数据")
            return 0
        return await self._write_to_clickhouse(data)
    except aiohttp.ClientError as e:
        logger.error(f"{code} 网络错误: {e}")
        return 0
    except Exception as e:
        logger.error(f"{code} 同步失败: {e}", exc_info=True)
        return 0
```

### 4.4 资源管理

```python
# ✅ 正确：使用 try...finally 确保释放
service = TickSyncService()
await service.initialize()
try:
    await service.sync_stocks(codes)
finally:
    await service.close()
```

---

## 5. 调度配置

### 5.1 tasks.yml 配置

```yaml
- id: daily_tick_sync
  name: 盘后分笔采集
  type: docker
  enabled: true
  schedule:
    type: trading_cron
    expression: "30 17 * * 1-5"  # 17:30 交易日
  target:
    command: ["jobs.sync_tick"]
    network_mode: "host"
    environment:
      MOOTDX_API_URL: "http://127.0.0.1:8000"
      CLICKHOUSE_HOST: "127.0.0.1"
      CLICKHOUSE_PORT: "9000"
  dependencies:
    - daily_kline_sync   # 依赖 K 线同步完成
  retry:
    max_attempts: 2
    backoff_seconds: 600
```

### 5.2 关键参数

| 参数 | 值 | 说明 |
|------|------|------|
| 执行时间 | 17:30 | 确保盘后数据稳定 |
| 并发数 | 3 | 避免压垮 mootdx |
| 重试次数 | 2 | 网络波动容错 |
| 重试间隔 | 600s | 10 分钟后重试 |

---

## 6. 数据质量检查

### 6.1 必检项

| 检查项 | SQL/方法 | 阈值 |
|--------|----------|------|
| 09:25 数据覆盖率 | `SELECT countIf(tick_time='09:25')/count(DISTINCT stock_code)` | > 99% |
| 每日 Tick 数 | `SELECT count() FROM tick_data WHERE trade_date = today()` | > 100万 |
| 空股票检测 | `SELECT stock_code ... HAVING count() < 100` | 需人工核查 |

### 6.2 异常处理

| 异常 | 原因 | 处理 |
|------|------|------|
| 09:25 缺失 | 搜索矩阵未覆盖 | 扩展矩阵范围 |
| 大量股票为 0 | mootdx 服务异常 | 检查服务状态，重试 |
| 重复数据 | 多次采集 | `ReplacingMergeTree` 自动去重 |

---

## 7. 监控与告警

### 7.1 日志规范

```python
# 开始
logger.info(f"开始采集 {len(codes)} 只股票的分笔数据 (日期: {date})")

# 进度
logger.info(f"[{current}/{total}] {code} 采集完成: {count} 条记录")

# 完成
logger.info(f"✅ 分笔采集完成: 成功 {success}/{total}, 总记录 {total_records}")
```

### 7.2 告警条件

| 条件 | 级别 | 动作 |
|------|------|------|
| 成功率 < 95% | ⚠️ Warning | 发送告警 |
| 成功率 < 50% | 🔴 Critical | 停止任务 + 人工介入 |
| 09:25 覆盖率 < 95% | 🔴 Critical | 检查搜索矩阵 |

---

## 8. 常见问题

### Q1: 为什么使用搜索矩阵而不是固定偏移？

> 不同股票的分笔数据量差异巨大（低活跃股 ~1000 条，高活跃股 ~5000+ 条），09:25 数据位置不可预测。

### Q2: 为什么并发数设为 3？

> 经验值。更高并发导致 mootdx 返回不完整数据。3 是稳定性和效率的平衡点。

### Q3: 为什么依赖 daily_kline_sync？

> K 线同步失败意味着数据源可能有问题。前置依赖可避免分笔采集无意义运行。

---

## 9. 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | 2026-01-06 | 初版发布 |

---

> **📌 提醒**: 本规范是活文档。如遇到新问题或优化，请及时更新。
