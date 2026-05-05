# 如何实现一个新的远程任务触发 (完整流程指南)

本文档详细描述了从零开始实现一个可通过云端 `task_commands` 表触发的新远程任务的完整代码流程。

## 1. 流程概览

实现一个新任务通常涉及以下三个层面的修改：

1.  **业务层 (`gsd-worker`)**: 编写实际执行业务逻辑的 Python 脚本 (Job)。
2.  **编排层 (`task-orchestrator`)**: 在 `config/tasks.yml` 中注册任务定义。
3.  **触发层 (MySQL)**: 在云端数据库插入命令进行触发。

*(可选: 如果需要“智能分片”或“自动联动”等高级特性，还需要修改 `CommandPoller` 代码)*

---

## 2. 详细步骤

### 步骤 1: 编写业务逻辑 (gsd-worker)

在 `services/gsd-worker/src/jobs/` 目录下创建新的任务脚本。例如：`example_job.py`。

关键点：
*   使用 `argparse` 接收命令行参数（这些参数将由 Poller 自动透传）。
*   实现 `main` 函数并处理业务逻辑。
*   正确设置退出码（0=成功, 非0=失败）。

```python
# services/gsd-worker/src/jobs/example_job.py
import argparse
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser()
    # 定义接收的参数 (对应 task_commands.params 中的 key)
    parser.add_argument("--target-date", type=str, required=True, help="目标日期")
    parser.add_argument("--mode", type=str, default="simple", help="运行模式")
    
    args = parser.parse_args()
    
    logger.info(f"🚀 开始执行示例任务: 日期={args.target_date}, 模式={args.mode}")
    
    # ... 执行具体业务逻辑 ...
    
    logger.info("✅ 任务完成")
    sys.exit(0)

if __name__ == "__main__":
    main()
```

### 步骤 2: 注册任务定义 (task-orchestrator)

在 `services/task-orchestrator/config/tasks.yml` 中添加任务配置。

关键点：
*   **id**: 全局唯一的任务 ID（云端 `task_id` 将引用此值）。
*   **command**: 指定 Docker 容器内执行的命令。
*   **enabled**: 对于仅远程触发的任务，通常设为 `false` 以避免自动调度。

```yaml
# services/task-orchestrator/config/tasks.yml

  # ... 其他任务 ...

  # 新增示例任务
  - id: example_remote_task
    name: 远程触发示例任务
    type: docker
    enabled: false  # 不自动运行，只等待远程触发
    schedule:
      type: cron
      expression: "0 0 1 1 *" # 占位符
    target:
      # 对应步骤 1 中的脚本
      # Poller 会自动将 JSON 参数追加到此命令后，例如: --target-date 20260101
      command: ["python", "-m", "jobs.example_job"]
      environment:
        LOG_LEVEL: "INFO"
    retry:
      max_attempts: 1
```

### 步骤 3: 重启编排服务

为了加载新的 `tasks.yml` 配置，必须重启 `task-orchestrator` 服务。

```bash
docker restart task-orchestrator
```

### 步骤 4: 触发与验证

现在可以通过云端 MySQL 触发该任务。CommandPoller 会自动完成参数映射。

**SQL 触发命令**:

```sql
INSERT INTO task_commands (task_id, params) 
VALUES ('example_remote_task', '{"target_date": "20260115", "mode": "full"}');
```

**执行过程 (CommandPoller 内部逻辑)**:
1.  Poller 轮询到新记录。
2.  读取 `params` JSON: `{"target_date": "20260115", "mode": "full"}`。
3.  自动转换为命令行参数列表: `["--target-date", "20260115", "--mode", "full"]`。
4.  将其追加到 `tasks.yml` 定义的 `command` 之后。
5.  最终 Docker执行命令: `python -m jobs.example_job --target-date 20260115 --mode full`。

---

## 3. 高级开发 (可选)

如果任务需要特殊的逻辑（例如：根据参数自动拆分为多个分片任务，或任务完成后自动触发其他任务），则需要修改 `input/task-orchestrator/src/core/command_poller.py`。

### 实现自定义分片逻辑

修改 `_process_pending_command` 方法，拦截特定 Task ID：

```python
# src/core/command_poller.py

async def _process_pending_command(self, cmd):
    # ...
    
    # === 自定义逻辑拦截 ===
    if task_id == "example_remote_task" and needs_splitting(cmd['params']):
        logger.info("🔪 检测到大任务，执行自动切分...")
        # 1. 拆分参数
        shards = split_params(cmd['params'])
        # 2. 插入新命令回云端
        for shard_param in shards:
             await self._insert_cloud_command("example_remote_task", shard_param)
        # 3. 标记当前父命令为 DONE
        return
        
    # ... 继续标准执行流程 ...
```

### 实现自动联动 (Re-Audit)

修改 `run` 方法中的任务完成回调部分：

```python
# src/core/command_poller.py

# ... 任务执行成功后 ...
if success:
    # 自动联动规则
    if task_id == "example_remote_task":
        logger.info("🔗 任务完成，自动触发后续检查...")
        await self._trigger_local_task("post_market_gate")
```

## 4. 调试建议

*   **查看 Poller 日志**: 
    `docker logs -f --tail 100 task-orchestrator | grep CommandPoller`
    确认是否收到了命令以及参数解析是否正确。
    查看业务脚本的实际执行输出。

## 5. AI 辅助开发提示词 (Prompt Template)

如果你希望让 AI 助手帮你快速生成新任务的代码，可以将以下提示词（Prompt）复制给它，填入你的具体需求即可：

---

**Role**: Senior Python Backend Engineer (FastAPI/Docker)

**Context**:
We are working on the `microservice-stock` project. I need to implement a new **Remote Trigger Task** that follows the `task-orchestrator` (scheduler) -> `gsd-worker` (execution) architecture.

**Requirement**:
Please implement a new task with the following specifications:

1.  **Task Information**:
    *   **Name**: [填写任务名称, 例如: 财务数据补采]
    *   **ID**: `[填写TaskID, 例如: repair_financial]`
    *   **Script Name**: `jobs.[填写脚本名, 例如: sync_financial]`

2.  **Job Logic (`gsd-worker`)**:
    *   Create a new Python script in `services/gsd-worker/src/jobs/`.
    *   Use `argparse` to accept the following parameters: `[列出参数, 例如: --date, --stock-codes]`
    *   Business Logic: [简要描述业务逻辑, 例如: 从 Tushare 拉取指定日期的财务数据并写入 ClickHouse]

3.  **Registration (`task-orchestrator`)**:
    *   Provide the YAML configuration snippet for `services/task-orchestrator/config/tasks.yml`.
    *   Set `enabled: false` (since it's a remote-only task).
    *   Ensure the command line arguments are correctly mapped from the input params.

**Deliverables**:
1.  Complete Python code for the job script.
2.  YAML configuration block for `tasks.yml`.
3.  A sample SQL `INSERT` statement for the `task_commands` table to test this task.

---



