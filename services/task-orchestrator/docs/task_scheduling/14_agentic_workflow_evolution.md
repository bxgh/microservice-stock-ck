# 任务调度 4.0：智能工作流引擎 (Agentic Workflow Engine)

> **版本**: 1.0 (Draft)  
> **状态**: 规划中 (Planned)  
> **基座**: 任务调度 3.0 (指令驱动架构)  
> **目标**: 进化为类似 n8n/Airflow 的智能编排系统，引入 AI 决策能力。

---

## 1. 愿景与目标

在 **架构 3.0** 中，我们成功实现了“指令驱动”模式，解决了分布式执行和单点调度的冲突。  
**架构 4.0** 的核心目标是将 **“指令生成”** 这一过程从硬编码的 Python 逻辑中解放出来，升级为**可配置、可编排、具备上下文感知**的智能工作流系统。

核心进化点：
1.  **逻辑图谱化**：从线性的 `Cron -> Task` 变为图状的 `Trigger -> Step A -> Decision -> Step B`。
2.  **上下文流转**：任务之间通过 `Context Bus` 传递数据（如：采集任务输出“缺失列表”，传递给修复任务）。
3.  **智能体介入**：允许 LLM 在工作流中担任“决策节点”，处理非结构化异常（如：分析日志决定是否切换代理）。

---

## 2. 核心概念 (Core Concepts)

### 2.1 Workflow (工作流)
定义业务逻辑的有向无环图 (DAG)。由一系列 **Step** (步骤) 和 **Edge** (流向) 组成。
*   **格式**: YAML / JSON 定义。
*   **特性**: 支持串行、并行、条件分支 (Switch)、循环。

### 2.2 Step (步骤/节点)
工作流中的最小执行单元。
*   **Action Step**: 执行具体动作（如 `run_docker`, `http_request`, `sql_query`）。
*   **Logic Step**: 流程控制（如 `wait`, `switch`, `merge`）。
*   **Agentic Step**: AI 决策节点（如 `analyze_error`, `generate_plan`）。

### 2.3 Context (上下文)
贯穿整个 Workflow 生命周期的 JSON 数据总线。
*   **Global Context**: 全局变量（如 `date`, `stock_list`）。
*   **Step Output**: 每个步骤执行完后，其结果会写入 Context，供后续步骤引用（例如 `{{steps.sync_tick.output.failed_count}}`）。

---

## 3. 架构设计 (Architecture)

系统由 **Controller (大脑)** 和 **Workers (手脚)** 组成，通过 **Database (神经中枢)** 交互。

```mermaid
graph TD
    subgraph "Master Node (Brain)"
        Trigger[Trigger (Cron/API)] --> Controller[Flow Controller]
        Controller <-->|Read/Write State| DB[(MySQL)]
        Agent[LLM Agent] <-->|Consult| Controller
    end

    subgraph "Data Store (Nervous System)"
        DB -->|Store Definitions| T_Def[workflow_definitions]
        DB -->|Track Instances| T_Run[workflow_runs]
        DB -->|Dispatch Commands| T_Cmd[task_commands (Smart)]
    end

    subgraph "Worker Nodes (Limbs)"
        W1[Worker 41] <-->|Poll & Ack| T_Cmd
        W2[Worker 58] <-->|Poll & Ack| T_Cmd
        W3[Worker 111] <-->|Poll & Ack| T_Cmd
    end
```

### 3.1 核心组件

1.  **Flow Controller (驻留 Node 41)**
    *   **职责**: 状态机引擎。不执行具体业务，只负责“翻页”。
    *   **逻辑**: 监听 `workflow_runs` 和 `task_commands` 的状态变化。当 Step A 完成 (Success)，Controller 读取流程定义，生成 Step B 的指令插入 `task_commands`。
2.  **Smart Workers (分布式)**
    *   **职责**: 执行具体的 `task_commands`。
    *   **升级**: 3.0 的 Worker 只把日志写入 DB。4.0 的 Worker 需要将**结构化输出 (Output JSON)** 回写到 DB，以便 Controller 传递给下一步。
3.  **Command Library (DB)**
    *   作为唯一的通信介质，确保分布式一致性和持久化。

---

## 4. 数据模型设计 (Database Schema)

### 4.1 `workflow_definitions` (流程定义表)
存储 YAML/JSON 格式的流程模板。

```sql
CREATE TABLE workflow_definitions (
    id VARCHAR(50) PRIMARY KEY, -- e.g., 'smart_tick_sync'
    name VARCHAR(100),
    version INT,
    definition JSON,            -- 完整的 DAG 定义
    created_at DATETIME
);
```

### 4.2 `workflow_runs` (流程实例表)
记录每一次工作流的执行状态。

```sql
CREATE TABLE workflow_runs (
    run_id UUID PRIMARY KEY,
    workflow_id VARCHAR(50),
    status VARCHAR(20),         -- PENDING, RUNNING, COMPLETED, FAILED
    context JSON,               -- 当前运行的全局上下文数据
    start_time DATETIME,
    end_time DATETIME
);
```

### 4.3 `task_commands` (指令表 - 3.0 升级版)
原有的指令表升级，增加上下文和流程关联。

```sql
ALTER TABLE task_commands ADD COLUMN run_id UUID;        -- 关联到 workflow_run
ALTER TABLE task_commands ADD COLUMN step_id VARCHAR(50); -- 对应流程中的节点 ID
ALTER TABLE task_commands ADD COLUMN input_context JSON;  -- 本步骤所需的输入参数
ALTER TABLE task_commands ADD COLUMN output_context JSON; -- 本步骤产生的输出结果
```

---

## 5. 工作流定义示例 (YAML)

以下是一个典型的 **“分笔采集 + 智能质检 + 自动修复”** 工作流：

```yaml
name: Distributed Tick Sync 4.0
verion: 1.0

inputs:
  - name: date
    type: string
    default: "today"

steps:
  # 步骤 1: 发射分片采集指令 (Fan-out)
  - id: dispatch_collect
    type: map            # Map 类型表示并行分发
    items: [0, 1, 2]     # Shards
    iterator: shard_id
    action: 
      type: command_emit
      template: "collect_tick_sharded"
      params:
        shard_id: "{{shard_id}}"
        date: "{{inputs.date}}"

  # 步骤 2: 等待所有分片完成 (Wait)
  - id: wait_for_collect
    type: wait
    depends_on: [dispatch_collect]
    condition: "all_success"

  # 步骤 3: 运行数据质量检查 (Python Action)
  - id: quality_check
    type: task
    depends_on: [wait_for_collect]
    worker_group: "master"
    command: "jobs.quality_check"
    params:
      date: "{{inputs.date}}"
    
  # 步骤 4: 逻辑分支 (Switch)
  - id: check_result_switch
    type: switch
    input: "{{steps.quality_check.output.status}}"
    cases:
      "PERFECT": [archive_data]
      "WARNING": [analyze_error]
      "CRITICAL": [alert_admin]

  # 分支 A: 智能分析 (Agentic Step)
  - id: analyze_error
    type: llm_agent
    input: "{{steps.quality_check.output.error_logs}}"
    prompt: "分析以下采集错误日志，如果是网络问题返回 'RETRY_PROXY'，如果是源文件缺失返回 'IGNORE'。"
  
  # 分支 A-1: 根据 LLM 建议行动
  - id: repair_action
    type: switch
    input: "{{steps.analyze_error.output.decision}}"
    cases: 
       "RETRY_PROXY": [retry_with_new_proxy]
       "IGNORE": [archive_data]

  # 终点: 归档
  - id: archive_data
    type: task
    command: "jobs.archive_day_data"
```

---

## 6. 实施路线图 (Roadmap)

### Phase 1: 基础建设 (Infrastructure)
*   **目标**: 让 Worker 能够读写 Context。
*   **任务**:
    1.  修改数据库 Schema，添加 `run_id`, `input_context`, `output_context`。
    2.  升级 `gsd-worker` 框架，支持从指令中读取 `input_context`，并将返回值序列化为 JSON 写入 DB。
    3.  标准化所有现有 Jobs 的返回值格式。

### Phase 2: 控制器实现 (The Controller)
*   **目标**: 实现一个最小化的流程引擎，替代 Cron。
*   **任务**:
    1.  开发 `FlowController` 服务 (Python)，轮询 DB。
    2.  实现基础的流程解析器 (支持 Linear 和 Map/Fan-out)。
    3.  迁移 `distributed_tick_sync` 任务到新的 Workflow 格式。

### Phase 3: 智能体集成 (Agent Integration)
*   **目标**: 引入 LLM 决策节点。
*   **任务**:
    1.  集成 LLM API (DeepSeek/GPT-4) 到 Controller。
    2.  定义 `AgentStep` 类型，支持 Prompt 模板。
    3.  设计并部署“智能异常自愈”工作流。

---

## 7. 总结

从 3.0 到 4.0 的跨越，本质上是将**“硬编码的业务流程”**转化为**“数据驱动的资产”**。这不仅让系统更灵活（修改流程无需改代码），更重要的是为 AI Agent 的介入提供了标准的接口（I/O Context），使得系统具备了进化和自我修复的能力。
