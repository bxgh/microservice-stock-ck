# Agentic Workflow 4.0 规划方案 (修正版)

抱歉，我之前的规划漏掉了 `daily_stock_collection` 在 08:45 的关键地位。你是对的，这是一个**盘前核心任务**，它是后续所有盘前门禁和系统预热的基础。

为了充分发挥 4.0 架构的优势，我们应该规划 **两个** 核心 Workflow：

---

## 1. 盘前准备管线：`Pre_Market_Preparation_4.0` (08:45)

这是系统的“唤醒服务”。

| 步骤 | 逻辑环节 | 对应任务 ID | 预计触发 | 优势 |
| :--- | :--- | :--- | :--- | :--- |
| **Step 1** | **名单采集** | `daily_stock_collection` | `08:45` | 获知今日是否有新股、退市或复牌。 |
| **Step 2** | **盘前门禁** | `pre_market_gate` | Step 1 成功后 | 校验名单，确保数据源 IP 池健康。 |
| **Step 3** | **缓存预热** | `daily_cache_warmup` | Step 2 成功后 | 预热 Redis 缓存，保证 09:30 开盘响应。 |

**AI 自愈点**：如果 08:45 采集失败，AI 会立即在分钟级内尝试重试，确保 09:15 门禁开始前名单必须到位。

---

## 2. 盘后数据管线：`Post_Market_Sync_4.0` (17:30 - 18:00)

这是系统的“收官与自愈”。

| 步骤 | 逻辑环节 | 对应任务 ID | 预计触发 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| **Step 1** | **日线同步** | `daily_kline_sync` | `17:30` | 每日收盘日线同步。 |
| **Step 2** | **分片分笔同步** | `collect_tick_sharded` | Step 1 成功后 | 分片并发采集 Tick 数据。 |
| **Step 3** | **盘后大门禁** | `post_market_gate` | Step 2 全部成功后 | 最终质量对账。 |

---

## 3. 任务调度表 (tasks.yml) 的调整建议

我们将不再维护这么多琐碎的 Cron，而是维护两个工作流触点。

### 盘前触发器配置：
```yaml
- id: trigger_pre_market_workflow
  name: 触发盘前 4.0 准备管线
  type: workflow_trigger
  schedule:
    type: cron
    expression: "45 8 * * 1-5"
  target:
    workflow_id: "pre_market_prep_4.0"
```

### 盘后触发器配置：
```yaml
- id: trigger_post_market_workflow
  name: 触发盘后 4.0 自愈管线
  type: workflow_trigger
  schedule:
    type: cron
    expression: "30 17 * * 1-5"
```

## 4. 下一步行动建议
如果你同意这个“双管线”方案，我将：
1. **定义这两个新工作流**：编写 `pre_market_prep_4.0.yml` 和 `post_market_sync_4.0.yml`。
2. **修改 `tasks.yml`**：启用新的工作流触发器并禁用旧的独立 Cron 任务。
3. **部署**：重启 Orchestrator。
