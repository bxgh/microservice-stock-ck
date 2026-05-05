# 4.0 模块化任务编排设计

## 1. 设计背景
随着系统任务增加到 20+ 个，原有的 `tasks.yml` 超过 400 行，维护极其困难。为了支持更灵活的代码协作和版本控制，我们引入了模块化加载机制。

## 2. 目录结构
配置文件现在集中在 `services/task-orchestrator/config/`：

```text
config/
├── main.yml                # 主控/全局配置
├── tasks/                  # 任务定义目录 (自动加载)
│   ├── 01_data_sync.yml    # 数据采集与同步任务
│   ├── 02_strategies.yml   # 策略执行与回测任务
│   ├── 03_maintenance.yml  # 数据审计与自愈维护任务
│   └── 04_workflow_triggers.yml # 时间点触发器
└── workflows/              # DAG 管线定义目录
    ├── pre_market_prep_4.0.yml
    └── post_market_audit.yml
```

## 3. 核心机制

### 3.1 动态加载
Orchestrator 启动时会执行以下逻辑：
1. 读取 `main.yml` 获取全局 Docker 环境变量、挂载卷和时区。
2. 扫描 `tasks/*.yml` 目录，解析所有任务定义。
3. 如果 `tasks.yml` (旧版) 存在且无新目录结构，则保持向后兼容。

### 3.2 环境隔离
通过模块化，我们可以为不同类别的任务定义不同的默认镜像或环境变量。例如：
- **数据同步**：侧重网络代理和 ClickHouse 吞吐。
- **策略扫描**：侧重 Numpy/Pandas 计算环境。

## 4. 关键原则
- **原子性**：`01_data_sync.yml` 中的任务应尽可能是原子的（如只负责下载，不负责校验）。
- **解耦调度**：业务逻辑任务（如 `daily_strategy_scan`）不应硬编码调度时间，应标记为 `enabled: true` 但使用 `Dummy Schedule`，由 `04_workflow_triggers.yml` 中的触发器配合 Workflow 驱动。

---
**更新日期**: 2026-02-04
