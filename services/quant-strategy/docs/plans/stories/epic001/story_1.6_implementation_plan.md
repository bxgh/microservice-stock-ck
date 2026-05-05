# Story 1.6: 任务调度集成与事件驱动框架实施方案

## 1. 目标描述

本 Story 旨在建立 `quant-strategy` 微服务的任务调度能力。为了避免重复建设系统，我们将采用分层调度策略：
1. **外部调度**: 对接现有的 `task-scheduler` 微服务，通过 HTTP API 触发低频/定时任务（如日线回测、盘后选股）。
2. **内部调度**: 实现基于 `asyncio` 的事件驱动框架，管理高频/实时任务（如 Tick 级信号监听、WebSocket 数据流处理）。

## 2. 核心组件设计

### 2.1 外部调度接口 (API Layer)

新增 API 端点供 `task-scheduler` 调用。

- `POST /api/v1/strategies/{strategy_id}/jobs/run`: 立即触发一次策略任务（如回测、日结）。
- `GET /api/v1/jobs/{job_id}`: 查询任务执行状态。
- `POST /api/v1/control/shutdown`: 优雅停机信号（可选，建议复用 k8s/docker stop 信号）。

### 2.2 内部后台任务管理器 (BackgroundTaskManager)

一个单例管理器，用于在 FastAPI `lifespan` 中启动和管理 `asyncio.Task`。

```python
class BackgroundTaskManager:
    """内部后台任务管理器"""
    def __init__(self):
        self._tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        
    async def start_task(self, name: str, coro: Coroutine):
        """启动一个后台常驻任务"""
        ...
        
    async def stop_task(self, name: str):
        """优雅停止指定任务"""
        ...
        
    async def shutdown(self):
        """关闭所有任务"""
        ...
```

### 2.3 简单事件总线 (EventBus)

用于解耦策略内部各组件（如数据接收 -> 信号生成 -> 交易执行）。

```python
class EventBus:
    """简单的内存事件总线"""
    async def publish(self, topic: str, event: Any): ...
    def subscribe(self, topic: str, callback: Callable): ...
```

## 3. 详细变更 (Proposed Changes)

### 3.1 基础设施 [INFRA]

#### [NEW] [manager.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/core/manager.py)
实现 `BackgroundTaskManager` 类。

#### [NEW] [event_bus.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/core/event_bus.py)
实现 `EventBus` 类。

### 3.2 接口层 [API]

#### [MODIFY] [strategy_routes.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/api/strategy_routes.py)
添加 `POST /run` 等调度相关接口。

### 3.3 主程序 [MAIN]

#### [MODIFY] [main.py](file:///home/bxgh/microservice-stock/services/quant-strategy/src/main.py)
在 lifespan 中集成 Manager 的启动和关闭。

## 4. 验证计划

### 4.1 单元测试
- 测试 `BackgroundTaskManager` 的任务启动、取消和异常隔离。
- 测试 `EventBus` 的订阅分发逻辑。

### 4.2 集成测试
- 启动服务，模拟 `task-scheduler` 发送 POST 请求触发策略，验证策略被正确执行。
- 验证 `Ctrl+C` 停机时后台任务能打印出清理日志。

