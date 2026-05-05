# 🚀 AI Quick Start

> **目的**: AI Agent 接手任务前，阅读本文档，1 分钟建立项目上下文。

---

## 项目一句话

**股票数据微服务平台**: 采集 A 股行情数据 → 存储 ClickHouse → 量化策略分析

---

## 技术栈核心

| 层次 | 技术 |
|------|------|
| **语言** | Python 3.12+ |
| **框架** | FastAPI + Asyncio |
| **存储** | ClickHouse (时序) / MySQL (元数据) / Redis (缓存) |
| **调度** | task-orchestrator (APScheduler) |
| **容器** | Docker + Docker Compose |
| **服务发现** | Nacos |

---

## 核心服务

| 服务 | 职责 | 端口 | 状态 |
|------|------|------|------|
| `get-stockdata` | 数据采集 (K线/Tick/财务) | 8083 | ✅ Active |
| `quant-strategy` | 策略引擎 (OFI/Smart Money) | 8084 | ✅ Active |
| `task-orchestrator` | 任务调度中心 | 18000 | ✅ Active |
| `mootdx-api` | 实时行情接口 | 8003 | ✅ Active |
| `mootdx-source` | 数据源适配 (gRPC) | 50051 | ✅ Active |
| `snapshot-recorder` | 快照记录 (Daemon) | - | ✅ Active |
| `gsd-api` | 数据查询 API | 8000 | ✅ Active |
| `gsd-worker` | 任务执行器 (临时容器) | - | 按需启动 |

---

## 关键编码规范

### ⚡ 异步优先
```python
# ✅ 正确
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        return await session.get(url)

# ❌ 错误 - 阻塞 I/O
def fetch_data():
    return requests.get(url)
```

### 🔒 共享状态必须加锁
```python
# ✅ 正确
self._lock = asyncio.Lock()
async with self._lock:
    self._shared_state = new_value

# ❌ 错误 - 无锁并发修改
self._shared_state = new_value
```

### 🕐 时区统一
```python
# ✅ 正确 - 始终使用上海时区
from datetime import datetime
import pytz
CST = pytz.timezone('Asia/Shanghai')
now = datetime.now(CST)

# ❌ 错误 - 使用 UTC 或本地时区
now = datetime.now()
```

### 🧹 资源管理
```python
# ✅ 正确 - 实现生命周期方法
class MyService:
    async def initialize(self): ...
    async def close(self): ...
    
# ✅ 正确 - try...finally 确保清理
try:
    conn = await get_connection()
    # 使用连接
finally:
    await conn.close()
```

---

## 交易时段

| 时段 | 时间 (Asia/Shanghai) |
|------|----------------------|
| 早盘 | 09:30 - 11:30 |
| 午盘 | 13:00 - 15:00 |
| 数据采集 | 15:05 开始 |

---

## 禁止操作 ⛔

- ❌ **未授权删除/修改生产数据** (见 `data_safety_policy.md`)
- ❌ **修改默认参数值** (如 adjustflag)
- ❌ **跳过测试直接部署**
- ❌ **使用全局可变状态而不加锁**

---

## 开发验证命令

```bash
# 运行测试 (在 Docker 中)
docker compose -f docker-compose.dev.yml run --rm get-stockdata pytest

# 检查服务健康
curl http://127.0.0.1:8000/health

# 查看日志
docker logs -f task-orchestrator
```

---

## 快速导航

| 需求 | 文档 |
|------|------|
| 理解服务架构 | [SERVICE_REGISTRY.md](./SERVICE_REGISTRY.md) |
| 数据流向 | [DATA_FLOW.md](./DATA_FLOW.md) |
| 当前进度 | [CURRENT_STATE.md](./CURRENT_STATE.md) |
| 历史决策 | [DECISION_LOG.md](./DECISION_LOG.md) |
| 技术债务 | [TECH_DEBT.md](./TECH_DEBT.md) |
| 数据安全规范 | [data_safety_policy.md](../ai_collaboration/data_safety_policy.md) |
