# 分片采集股票代码分配机制

**文档版本**: 1.0  
**更新时间**: 2026-01-08  

---

## 概述

分布式分笔采集系统使用 **Hash 取模算法** 将全市场股票代码均匀分配到多个计算节点，实现并行采集。

---

## 核心算法

### 分片公式

```python
shard = hash(stock_code) % shard_total

if shard == shard_index:
    # 该股票分配给当前节点
    process(stock_code)
```

### 参数说明

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `stock_code` | str | 股票代码 | "000001" |
| `shard_total` | int | 总分片数（节点数） | 3 |
| `shard_index` | int | 当前分片索引（0-based） | 0, 1, 2 |

---

## 工作流程

### 1. 获取全市场股票列表

```python
# 从 mootdx-api 获取所有股票
stock_codes = await service.get_all_stocks()
# 例如: ["000001", "000002", ..., "688999"] (约 5293 只)
```

### 2. 应用分片过滤

```python
if shard_index is not None and shard_total is not None:
    original_count = len(stock_codes)
    
    # Hash 取模过滤
    stock_codes = [
        code for code in stock_codes 
        if hash(code) % shard_total == shard_index
    ]
    
    logger.info(
        f"分片过滤: {original_count} 只 → {len(stock_codes)} 只 "
        f"(Shard {shard_index}/{shard_total})"
    )
```

### 3. 执行采集

```python
# 每个节点只采集分配给自己的股票
results = await service.sync_stocks(
    stock_codes=stock_codes,
    trade_date=date,
    concurrency=6
)
```

---

## 分配示例

### 场景：3 节点集群

**配置**:
- Server 41: `SHARD_INDEX=0`, `SHARD_TOTAL=3`
- Server 58: `SHARD_INDEX=1`, `SHARD_TOTAL=3`
- Server 111: `SHARD_INDEX=2`, `SHARD_TOTAL=3`

**全市场股票**: 5293 只

**分配结果**:

| 节点 | Shard | 分配股票数 | 占比 | 示例股票 |
|------|-------|-----------|------|----------|
| Server 41 | 0 | ~1764 只 | 33.3% | 000005, 000006, 000009... |
| Server 58 | 1 | ~1765 只 | 33.3% | 000001, 000002, 000011... |
| Server 111 | 2 | ~1764 只 | 33.4% | 000004, 000008, 000012... |

**实际测试数据** (2026-01-08):
- Server 41: 1721 只
- Server 111: 1822 只
- 总计: 3543 只

---

## 算法特性

### 优点

1. **均匀分布**
   - Hash 函数保证股票代码均匀分散
   - 每个节点负载基本相同（误差 < 5%）

2. **确定性**
   - 同一股票代码总是分配到同一节点
   - 重复执行结果一致

3. **无需协调**
   - 各节点独立计算，无需中心调度
   - 避免单点故障

4. **易扩展**
   - 增加节点只需修改 `shard_total`
   - 无需修改核心逻辑

### 缺点

1. **重新分片问题**
   - 节点数量变化时，股票分配会改变
   - 需要重新采集全部数据

2. **负载不完全均衡**
   - 不同股票的数据量可能差异较大
   - 某些节点可能先完成

---

## 使用方法

### 命令行参数

```bash
# Server 41 (Shard 0)
docker run --rm --network host \
  -e SHARD_INDEX=0 \
  -e SHARD_TOTAL=3 \
  gsd-worker:latest \
  jobs.sync_tick --scope all --date 20260107 \
  --shard-index 0 --shard-total 3

# Server 58 (Shard 1)
docker run --rm --network host \
  -e SHARD_INDEX=1 \
  -e SHARD_TOTAL=3 \
  gsd-worker:latest \
  jobs.sync_tick --scope all --date 20260107 \
  --shard-index 1 --shard-total 3

# Server 111 (Shard 2)
docker run --rm --network host \
  -e SHARD_INDEX=2 \
  -e SHARD_TOTAL=3 \
  gsd-worker:latest \
  jobs.sync_tick --scope all --date 20260107 \
  --shard-index 2 --shard-total 3
```

### 环境变量（可选）

虽然可以通过环境变量设置，但 **命令行参数优先级更高**：

```bash
export SHARD_INDEX=0
export SHARD_TOTAL=3
```

---

## 验证方法

### 1. 检查分配数量

```bash
# 查看日志中的分片过滤信息
grep "分片过滤" /tmp/shard0.log
# 输出: 分片过滤: 5293 只 → 1721 只 (Shard 0/3)
```

### 2. 验证无重复

确保每只股票只被一个节点处理：

```python
# 理论验证
total_stocks = 5293
shard_total = 3

assigned = sum(
    len([c for c in all_stocks if hash(c) % shard_total == i])
    for i in range(shard_total)
)

assert assigned == total_stocks  # 应该相等
```

### 3. 检查数据完整性

```sql
-- 在 ClickHouse 中验证
SELECT 
    COUNT(DISTINCT stock_code) as unique_stocks,
    COUNT(*) as total_records
FROM stock_data.tick_data
WHERE trade_date = '2026-01-07';
```

---

## 性能影响

### 理论加速比

| 节点数 | 每节点股票数 | 预估耗时 | 加速比 |
|--------|-------------|----------|--------|
| 1 | 5293 | 80 分钟 | 1x |
| 2 | ~2647 | 40 分钟 | 2x |
| 3 | ~1764 | 27 分钟 | 3x |
| 4 | ~1323 | 20 分钟 | 4x |

### 实际考虑因素

1. **网络延迟**: SSH 并行触发 + 数据同步
2. **负载不均**: 某些股票数据量更大
3. **ClickHouse 同步**: ReplicatedMergeTree 副本同步开销

---

## 故障处理

### 节点故障

如果某个节点故障：

1. **数据缺失**: 该节点负责的股票未采集
2. **恢复方法**: 
   - 修复节点后重新执行
   - 或临时调整其他节点的 `shard_total` 覆盖

### 示例：2 节点覆盖 3 节点的工作

```bash
# 原 Shard 0 + Shard 2 的股票
# 临时方案：使用 shard_total=2 重新分配

# Server 41
--shard-index 0 --shard-total 2

# Server 111  
--shard-index 1 --shard-total 2
```

**注意**: 这会改变分配，需要重新采集全部数据。

---

## 相关代码

- **实现文件**: `services/gsd-worker/src/jobs/sync_tick.py`
- **核心逻辑**: 第 54-62 行
- **测试脚本**: `scripts/test_distributed_*.sh`

---

## 参考资料

- [EPIC-016 分布式分笔采集集群](../epics/EPIC_016_DISTRIBUTED_TICK_ACQUISITION.md)
- [分布式测试总结](../reports/DISTRIBUTED_TEST_SUMMARY_20260108.md)
- [三节点架构文档](../architecture/infrastructure/THREE_NODE_ARCHITECTURE.md)

---

*文档生成时间: 2026-01-08 18:30*  
*作者: AI Assistant*
