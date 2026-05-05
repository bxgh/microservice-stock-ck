# 设计文档：指定日期历史分笔数据采集 (V4.0 指令驱动模式)

## 0. 设计目标
本专题旨在实现一套独立于当日调度、由 `task_command` 驱动的历史分笔数据采集方案。该方案需具备高精准度、物理安全及性能可控性，且严禁修改当日（盘后）采集的任何生产代码。

---

## 1. 核心执行逻辑 (Task Command Pipeline)

历史日期采集不通过 Cron 触发，而是由 `CommandPoller` 监听 `alwaysup.task_commands` 表中的指令执行。

### 1.1 指令触发形态
```json
{
  "task_id": "repair_tick",
  "params": {
    "date": "20260128", 
    "mode": "full",
    "scope": "all",
    "concurrency": 60,
    "force": true
  }
}
```

### 1.2 执行流水线 (Node 41 独占执行)

1.  **参数标准化**: 接收指令，将日期统一标准化为 `YYYYMMDD` 格式。
2.  **动态名单反推 (Dynamic Universe)**:
    - **逻辑**: 调用 `get_today_traded_stocks(target_date)`。
    - **数据源**: 优先访问当日已入库的 K 线数据（ClickHouse `stock_kline_daily`）。
    - **代码标准化 (Standardization)**: 提取的原始代码必须强制转换为 **TDX 标准 6 位纯数字模式**（无 `SH/SZ` 前缀，无 `.SH/.SZ` 后缀）。
    - **北证过滤 (Critical)**: 在标准代码基础上，强制使用 `LIKE '4%'`, `LIKE '8%'`, `LIKE '9%'` 过滤规则剔除北交所股票。
3.  **物理清理 (Atomic Purge)**:
    - **操作**: 执行 `ALTER TABLE stock_data.tick_data ON CLUSTER stock_cluster DELETE WHERE trade_date = 'target_date'`。
    - **集群同步**: 使用 `ON CLUSTER` 确保所有分片服务器上的指定日期历史数据同步清理，防止旧分片保留残留数据。
    - **安全**: 仅在 `mode=full` 且本节点为主控时下发，规避 Mutation 堆积风险。
4.  **高并发补采**:
    - **并发数**: 锁定为 **60**。
    - **API 适配**: `TickFetcher` 自动识别为历史模式（V3 矩阵拼缝），采用 800/600 重叠分片扫描。
    - **执行约束 (Immutable)**: 该采集模式已由 `mootdx-api` 底层代码固化实现。**除非重大性能优化且经过用户明确审计确认，严禁修改任何相关代码**。
5.  **质量审计 (Ad-hoc Audit)**:
    - 采集完成后，针对该指定日期触发专项审计，确认覆盖率（剔除北证）。
6.  **AI 介入二次自愈 (Resilient Self-Healing)**:
    - **分级决策逻辑 (Tiered Recovery)**:
        - **大面积异常 (> 200 只 Invalid)**: 判定为系统性环境波动或 API 拥堵，**直接触发全量补采模式** (`repair_tick`)，不再逐一执行 AI 分析。
        - **局部漏采 (<= 200 只 Invalid)**: 判定为个股数据抖动，**启动 AI 研判流程**：
            - **AI 研判**: 将异常名单推送至 `ai_quality_gatekeeper`。
            - **逻辑决策**: AI 结合历史挂牌、停牌信息，确认“真实漏采”。
            - **AI 容错 (Fail-safe)**: 若 AI 服务不可用或超时，**严禁降级为 5000 只全量补采**。系统应保持克制，直接将当前审计发现的异常名单 (<= 200 只) 全部判定为“待修复”，执行一次定向补采指令 (`stock_data_supplement`)。
            - **精准二轮补采**: 针对确认漏采名单，下发一次低并发定向补采指令。
    - **目标**: 确保最终准确度无限接近 100%。

---

## 2. 系统约束与安全性 (Constraints)

- **当日代码隔离**: 所有针对历史日期的特殊开关（如特定过滤优化）必须封装在 `TickSyncService` 的历史参数路径下，不得干扰当日 17:30 的 `incremental` 同步逻辑。
- **北证彻底剔除**: 无论是名单获取还是最终审计，北交所代码均不得参与计算，确保沪深 A 股指标的纯洁性。
- **Mutation 限流**: 历史清理指令需具备去重检查，5 分钟内同一分区的清理指令严禁重复下发。

---

## 3. 待讨论事项
- Q1: 如果某历史日期完全没有 K 线数据，应降级到哪种名单？
    - **结论**: 降级使用 **Node 41 服务器 Redis 缓存的 A 股代码名单** (`metadata:stock_codes`)，即便如此也必须执行 6 位标准化及北证过滤。
- Q2: 历史补采是否需要开启 Redis 队列模式？
    - **结论**: **不需要**。保持单节点 Node 41 直接高并发采集模式，以简化任务追踪与状态反馈。
