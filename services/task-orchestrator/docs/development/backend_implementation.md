# Task Orchestrator 后端开发计划

**版本**: v1.0  
**创建时间**: 2026-01-14  
**负责人**: Backend Team  
**预计工时**: 13 小时

---

## 一、开发目标

为 Task Orchestrator 服务增加以下后端能力：
1. **任务控制 API**：手动触发、暂停、恢复任务
2. **配置热重载**：无需重启服务即可更新任务定义
3. **自动告警集成**：任务失败时自动发送 Webhook 通知
4. **Dashboard 数据 API**：为前端提供任务状态、历史和依赖数据

---

## 二、现有基础设施

✅ **已完成模块**（可直接复用）：
- `TaskLogger` ([logger_service.py](file:///home/bxgh/microservice-stock/services/task-orchestrator/src/core/logger_service.py))：任务执行日志记录到 MySQL
- `Notifier` ([notifier.py](file:///home/bxgh/microservice-stock/services/task-orchestrator/src/core/notifier.py))：Webhook 告警（企业微信/飞书）
- `Task API` ([tasks.py](file:///home/bxgh/microservice-stock/services/task-orchestrator/src/api/tasks.py))：基础任务 API

---

## 三、开发任务清单

### 任务 1: 任务控制 API 增强 (优先级: P0)

**工时**: 3 小时

#### 1.1 修改文件
- [MODIFY] `src/api/tasks.py`

#### 1.2 实现内容

##### 增强 `POST /api/v1/tasks/{task_id}/trigger`
**当前行为**: 修改 `next_run_time` 为现在  
**改进行为**: 直接异步执行任务，不干扰原定时计划

**代码示例**：
```python
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
import asyncio

@router.post("/tasks/{task_id}/trigger")
async def trigger_task(task_id: str, params: Optional[Dict[str, Any]] = None):
    """
    立即执行一次任务（不影响原调度计划）
    
    Args:
        task_id: 任务ID
        params: 可选参数，用于补采场景（如 {"date": "20260113"}）
    """
    from main import scheduler
    
    job = scheduler.get_job(task_id)
    if not job:
        raise HTTPException(404, f"Task {task_id} not found")
    
    # 异步触发，立即返回
    asyncio.create_task(job.func())
    
    return {
        "status": "triggered",
        "task_id": task_id,
        "params": params,
        "message": "任务已提交执行"
    }
```

##### 新增 `POST /api/v1/tasks/{task_id}/pause`
**功能**: 暂停任务的自动调度（已启动的容器不会停止）

```python
@router.post("/tasks/{task_id}/pause")
async def pause_task(task_id: str):
    """暂停任务自动调度"""
    from main import scheduler
    
    try:
        scheduler.pause_job(task_id)
        return {"status": "paused", "task_id": task_id}
    except Exception as e:
        raise HTTPException(500, f"Failed to pause task: {str(e)}")
```

##### 新增 `POST /api/v1/tasks/{task_id}/resume`
**功能**: 恢复任务的自动调度

```python
@router.post("/tasks/{task_id}/resume")
async def resume_task(task_id: str):
    """恢复任务自动调度"""
    from main import scheduler
    
    try:
        scheduler.resume_job(task_id)
        return {"status": "resumed", "task_id": task_id}
    except Exception as e:
        raise HTTPException(500, f"Failed to resume task: {str(e)}")
```

#### 1.3 测试要求
- 创建 `tests/test_task_control.py`
- 测试用例：
  - ✅ 触发任务：验证异步执行不阻塞
  - ✅ 暂停任务：验证下次调度被跳过
  - ✅ 恢复任务：验证调度重新生效
  - ✅ 边界情况：不存在的 task_id

---

### 任务 2: 配置热重载 (优先级: P0)

**工时**: 4 小时

#### 2.1 新建文件
- [NEW] `src/core/config_reloader.py`

#### 2.2 实现内容

##### 核心逻辑
```python
"""
配置热重载模块
支持增量更新 APScheduler 中的任务定义
"""

import logging
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)

async def reload_task_config() -> dict:
    """
    热重载任务配置，增量更新 Scheduler
    
    Returns:
        dict: 变更摘要 {"added": [...], "removed": [...], "modified": [...]}
    """
    from main import task_config, scheduler, register_jobs
    from config.task_loader import TaskLoader
    
    logger.info("🔄 Starting configuration reload...")
    
    # 1. 重新加载 YAML
    config_path = Path(__file__).parent.parent.parent / "config" / "tasks.yml"
    loader = TaskLoader()
    new_config = loader.load_from_yaml(str(config_path))
    
    # 2. Diff 旧配置与新配置
    old_ids: Set[str] = {t.id for t in task_config.tasks}
    new_ids: Set[str] = {t.id for t in new_config.tasks}
    
    added = new_ids - old_ids
    removed = old_ids - new_ids
    potentially_modified = old_ids & new_ids
    
    # 3. 删除已移除的任务
    for removed_id in removed:
        scheduler.remove_job(removed_id)
        logger.info(f"🗑️ Removed job: {removed_id}")
    
    # 4. 更新全局配置
    task_config.tasks = new_config.tasks
    
    # 5. 重新注册所有任务（add_job 的 replace_existing=True 会覆盖）
    await register_jobs()
    
    logger.info(f"✅ Configuration reloaded: +{len(added)} -{len(removed)}")
    
    return {
        "added": list(added),
        "removed": list(removed),
        "modified": list(potentially_modified)
    }
```

#### 2.3 API 端点
- [MODIFY] `src/api/tasks.py`

```python
from core.config_reloader import reload_task_config

@router.post("/reload")
async def reload_config():
    """热重载任务配置"""
    from datetime import datetime
    
    try:
        changes = await reload_task_config()
        return {
            "status": "reloaded",
            "changes": changes,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(500, f"Reload failed: {str(e)}")
```

#### 2.4 测试要求
- 创建 `tests/test_config_reload.py`
- 测试用例：
  - ✅ 新增任务：验证 Scheduler 中出现新 Job
  - ✅ 删除任务：验证 Job 被移除
  - ✅ 修改调度：验证 Cron 表达式更新

---

### 任务 3: 自动告警集成 (优先级: P1)

**工时**: 2 小时

#### 3.1 修改文件
- [MODIFY] `src/main.py`

#### 3.2 实现内容

##### 在 `register_jobs()` 后添加监听器
```python
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED
from core.notifier import notifier

async def job_failure_listener(event):
    """任务失败监听器"""
    if event.exception:
        job = scheduler.get_job(event.job_id)
        job_name = job.name if job else event.job_id
        
        await notifier.send_alert(
            title=f"⚠️ 任务执行失败: {job_name}",
            message=(
                f"**任务ID**: {event.job_id}\n"
                f"**异常信息**: {str(event.exception)[:500]}\n"
                f"**时间**: {event.scheduled_run_time}\n"
            ),
            level="error"
        )

# 在 lifespan() 的 register_jobs() 之后添加
scheduler.add_listener(
    job_failure_listener,
    EVENT_JOB_ERROR | EVENT_JOB_MISSED
)
logger.info("✓ Alert listener registered")
```

#### 3.3 测试要求
- 创建 `tests/test_alerting_integration.py`
- 使用 `httpx_mock` 或 `respx` Mock Webhook URL
- 验证异常触发时 Webhook 被调用

---

### 任务 4: Dashboard 数据 API (优先级: P1)

**工时**: 3 小时

#### 4.1 新建文件
- [NEW] `src/api/dashboard_routes.py`

#### 4.2 实现内容

```python
"""
Dashboard 数据接口
为前端提供任务状态、执行历史、依赖关系等数据
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Any

router = APIRouter()

@router.get("/dashboard")
async def serve_dashboard():
    """提供 Dashboard 静态页面"""
    static_path = Path(__file__).parent.parent / "static" / "dashboard.html"
    if not static_path.exists():
        raise HTTPException(404, "Dashboard not found")
    return FileResponse(static_path)

@router.get("/api/v1/dashboard/overview")
async def get_overview() -> Dict[str, Any]:
    """
    系统总览
    
    Returns:
        {
          "total_tasks": 10,
          "enabled_tasks": 8,
          "running_tasks": 3,
          "today_failures": 1,
          "scheduler_status": "running"
        }
    """
    from main import task_config, scheduler, mysql_pool
    
    jobs = scheduler.get_jobs()
    running_count = len([j for j in jobs if j.next_run_time])
    
    # 查询今日失败次数
    today_failures = 0
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT COUNT(*) FROM task_execution_logs "
                    "WHERE status = 'FAILED' AND DATE(start_time) = %s",
                    (date.today(),)
                )
                result = await cursor.fetchone()
                today_failures = result[0] if result else 0
    except Exception as e:
        logger.warning(f"Failed to query today_failures: {e}")
    
    return {
        "total_tasks": len(task_config.tasks),
        "enabled_tasks": len([t for t in task_config.tasks if t.enabled]),
        "running_tasks": running_count,
        "today_failures": today_failures,
        "scheduler_status": "running" if scheduler.running else "stopped"
    }

@router.get("/api/v1/dashboard/dag")
async def get_dag() -> Dict[str, Any]:
    """
    返回任务依赖 DAG 结构
    
    Returns:
        {
          "nodes": [{"id": "task_1", "name": "K线同步"}],
          "edges": [{"from": "task_1", "to": "task_2"}]
        }
    """
    from main import task_config
    
    nodes = []
    edges = []
    
    for task in task_config.tasks:
        nodes.append({
            "id": task.id,
            "name": task.name,
            "type": task.type.value,
            "enabled": task.enabled
        })
        
        # 如果任务有 dependencies 字段
        if hasattr(task, 'dependencies') and task.dependencies:
            for dep in task.dependencies:
                edges.append({"from": dep, "to": task.id})
    
    return {"nodes": nodes, "edges": edges}
```

#### 4.3 注册路由
- [MODIFY] `src/main.py`

```python
# 在 app.include_router(tasks_router, ...) 之后添加
from api.dashboard_routes import router as dashboard_router
app.include_router(dashboard_router, tags=["dashboard"])
```

---

## 四、验证计划

### 4.1 单元测试
```bash
# 在容器内执行
pytest tests/test_task_control.py -v
pytest tests/test_config_reload.py -v
pytest tests/test_alerting_integration.py -v
```

### 4.2 集成测试（手动）

**测试配置热重载**：
```bash
# 1. 修改 config/tasks.yml，增加测试任务
# 2. 调用重载 API
curl -X POST http://localhost:18000/api/v1/reload

# 3. 验证任务列表
curl http://localhost:18000/jobs
```

**测试任务控制**：
```bash
# 手动触发
curl -X POST http://localhost:18000/api/v1/tasks/daily_stock_collection/trigger

# 暂停任务
curl -X POST http://localhost:18000/api/v1/tasks/weekly_deep_audit/pause

# 恢复任务
curl -X POST http://localhost:18000/api/v1/tasks/weekly_deep_audit/resume
```

**测试告警**：
```bash
# 临时修改某任务命令为错误命令
# 等待任务触发失败
# 检查企业微信 Webhook 是否收到告警
```

---

## 五、开发进度跟踪

| 任务 | 状态 | 负责人 | 开始时间 | 完成时间 | 备注 |
|-----|------|--------|----------|----------|------|
| 任务控制 API | ⬜ 待开始 | - | - | - | - |
| 配置热重载 | ⬜ 待开始 | - | - | - | - |
| 自动告警集成 | ⬜ 待开始 | - | - | - | - |
| Dashboard 数据 API | ⬜ 待开始 | - | - | - | - |
| 单元测试 | ⬜ 待开始 | - | - | - | - |
| 集成测试 | ⬜ 待开始 | - | - | - | - |

**状态图例**: ⬜ 待开始 | 🟡 进行中 | ✅ 已完成 | ❌ 已阻塞

---

## 六、技术注意事项

> [!WARNING]
> **配置热重载行为**：重载仅影响未来的调度，正在运行的任务不会被中断。

> [!IMPORTANT]
> **任务暂停机制**：APScheduler 的 `pause_job()` 仅阻止调度触发，已启动的容器任务不会被杀死。如需中止运行中的任务，需额外实现容器停止逻辑（建议 V2 支持）。

> [!NOTE]
> **并发安全**：`task_config` 是全局对象，在 `reload_task_config()` 中修改时需考虑并发场景。当前 APScheduler 使用单线程事件循环，暂无并发问题。

---

## 七、API 文档

完整的 API 文档将在开发完成后更新到：
- Swagger UI: `http://localhost:18000/docs`
- ReDoc: `http://localhost:18000/redoc`
