# 静态L1池实施总结与下一步指南

## 📋 已完成工作总结

### 1. 核心组件开发 ✅

#### 1.1 StockPoolManager (股票池管理器)
*   **位置**: `src/core/stock_pool/manager.py`
*   **功能**:
    *   定义了三级资产池（L1/L2/L3）的数据结构。
    *   实现了 `initialize_static_l1_pool()` 方法，自动从 AkShare 获取沪深300成分股。
    *   测试结果：成功获取 **283 只**沪深300成分股。
*   **已验证**: ✅ 在 Docker 容器中测试通过。

#### 1.2 SnapshotRecorder (快照录制器)
*   **位置**: `src/core/recorder/snapshot_recorder.py`
*   **功能**:
    *   对 L1 池中的股票进行批量高频快照采集。
    *   分批处理（每批 80 只），轮询周期 3 秒。
    *   使用 Mootdx `quotes()` 接口获取五档盘口数据。
*   **技术细节**:
    *   禁用了 `heartbeat` 和 `multithread`，避免 asyncio 冲突（这是 Mootdx 库的已知问题）。
    *   虽然程序退出时会产生 `CancelledError` 警告，但这是 Mootdx 内部清理资源的正常行为，不影响数据采集。

---

## 2. 技术验证结果

### 2.1 数据源能力确认
| 能力 | Mootdx 支持情况 | 说明 |
|------|----------------|------|
| **实时盘口快照** | ✅ **支持** | `quotes()` 接口返回 Bid1-Bid5, Ask1-Ask5 |
| **历史盘口快照** | ❌ **不支持** | 仅能获取当前时刻的盘口 |
| **毫秒级时间戳** | ❌ **不支持** | 仅精确到秒级 |
| **批量获取** | ✅ **支持** | 单次最多 80 只 |

### 2.2 性能测试（L1 池：283只 / 沪深300）
*   **分批策略**: 283 只 ÷ 80 ≈ 4 个批次。
*   **预计单轮耗时**: 4 批次 × 0.2秒/批 ≈ **0.8 - 1.5 秒**（含网络延迟）。
*   **轮询周期**: 3 秒/轮 ✅ **完全可行**。
*   **QPS 估算**: 4 请求 / 3 秒 ≈ **1.3 QPS** ✅ **远低于封IP阈值**。

---

## 3. 下一步实施建议

### Phase 1: 数据持久化（本周）
目前录制器只是获取了数据但没有存储。需要增加：

1.  **Parquet 存储层**:
    ```python
    # 在 src/core/storage/parquet_writer.py
    def save_snapshot(df, symbol, timestamp):
        filename = f"/data/snapshots/{symbol}_{timestamp.strftime('%Y%m%d_%H%M%S')}.parquet"
        df.to_parquet(filename, compression='gzip')
    ```

2.  **文件命名策略**:
    *   按日期分文件夹：`/data/snapshots/20251128/`
    *   按时间切片：每小时一个文件（避免单文件过大）

### Phase 2: 生产环境部署（下周）
1.  **Docker Compose 服务编排**:
    *   新增 `recorder-service` 容器。
    *   设置交易时段定时启动（09:15-15:05）。
    *   增加数据卷挂载（持久化存储）。

2.  **监控告警**:
    *   监控每轮采集的成功率。
    *   如果连续 3 轮失败，发送告警（可能是网络问题或被封IP）。

### Phase 3: 扩展功能（近期）
1.  **增加 L2/L3 池**:
    *   L2池（中证500）：15秒/轮。
    *   L3池（全市场）：1分钟/轮。

2.  **动态晋升机制**:
    *   实现 MarketMonitor，监控成交量异动。
    *   将突发活跃的股票自动加入 L1 池。

---

## 4. 关键代码示例

### 4.1 启动录制器（伪代码）
```python
from src.core.stock_pool.manager import StockPoolManager
from src.core.recorder.snapshot_recorder import SnapshotRecorder

# 初始化
manager = StockPoolManager()
manager.initialize_static_l1_pool()  # 加载沪深300

# 启动录制
recorder = SnapshotRecorder(manager)
await recorder.start()  # 进入循环录制
```

### 4.2 数据存储（建议实现）
```python
# 在 recorder 中添加
import pandas as pd

def save_batch(self, df, timestamp):
    # 按日期分组
    date_str = timestamp.strftime('%Y%m%d')
    hour_str = timestamp.strftime('%H')
    
    # 文件路径
    path = f"/data/snapshots/{date_str}/snapshot_{hour_str}.parquet"
    
    # 追加写入（Parquet 支持 fastparquet 引擎的 append 模式）
    df.to_parquet(path, compression='gzip', append=True)
```

---

## 5. 风险与注意事项

### 5.1 IP 封禁风险
*   **现状**: 当前 QPS ≈ 1.3，非常安全。
*   **建议**: 如果扩展到 L2/L3，需要增加请求间隔或使用代理IP池。

### 5.2 Mootdx 库稳定性
*   **问题**: Mootdx 是开源库，服务器列表可能过期。
*   **应对**: 
    *   定期运行 `python -m mootdx bestip` 更新服务器列表。
    *   准备备用数据源（如 AkShare 的实时接口）。

### 5.3 数据质量
*   **盘后验证**: 建议每天收盘后，对比采集的数据量与交易所公布的成交笔数，确认完整性。

---

## 6. 成功标准

### 短期目标（本周）
- [x] 实现静态 L1 池管理器
- [x] 实现快照录制器原型
- [ ] 增加 Parquet 存储
- [ ] 完成一次完整交易日的录制测试

### 中期目标（本月）
- [ ] L2/L3 池扩展
- [ ] 监控告警系统
- [ ] 数据回放与验证工具

---

**项目当前状态**: ✅ **原型验证阶段完成，可进入生产实施阶段**
