# Systemic Refactoring Prompt: Unified Tick Data Acquisition (v2.1)

> **用途**: 将此提示词发送给 AI 助手，以执行分笔数据系统的标准化重构。  
> **版本**: 2.1 (增加股票代码规范)

---

## Role

You are an **Expert Python Backend Architect** specializing in:
- High-Frequency Trading systems
- `asyncio` concurrent programming
- `ClickHouse` distributed database optimization
- Microservices design patterns

---

## Context

### Current System Architecture

We maintain a distributed A-Share tick data acquisition system with **three scenarios**:

| 场景 | 服务 | 运行模式 | 数据源API | 写入目标 |
|------|------|---------|----------|---------|
| **盘中实时** | get-stockdata | 常驻容器 (09:25-15:00) | `/api/v1/tick/{code}` | `stock_tick_data_local` |
| **盘后当天** | gsd-worker | 定时任务 (15:35, 19:18) | `/api/v1/tick/{code}` | `tick_data_intraday` (分布式) |
| **盘后历史** | gsd-worker | 手动/周审计 | `/api/v1/tick/{code}?date=YYYYMMDD` | `tick_data` (分布式) |

### Core Problems

| # | 问题 | 严重程度 | 影响 |
|---|------|---------|------|
| **P1** | API 路径错误 | 🔴 严重 | `get-stockdata/tick_worker.py:125` 使用不存在的 `/api/v1/ticks` |
| **P2** | 表命名不对应 | 🟡 中等 | 本地表 `stock_tick_data_local` 与分布式表 `tick_data_intraday` 命名风格不统一 |
| **P3** | 代码重复 | 🟡 中等 | 两个服务各自实现 Fetcher/Writer，逻辑不一致 (MD5 vs 元组去重) |
| **P4** | 字段映射不统一 | 🟢 低 | Direction 字段处理 logic 不同 |
| **P5** | 股票代码格式不统一 | 🟢 低 | `lstrip('sh')` vs `lstrip('.')` |

---

## Objective

建立 `gsd-shared/tick` 共享库，统一三种场景的核心采集逻辑，确保：
1. **Single Source of Truth**: 所有服务使用相同的 Fetcher/Writer 实现
2. **Consistent Schema**: 表命名遵循 `{purpose}_local` / `{purpose}` (分布式) 规范
3. **Unified Format**: 股票代码统一为纯数字格式 (6位)

---

## Constraints (不可变)

| 约束 | 说明 |
|------|------|
| **分布式架构** | 不得修改 ClickHouse 分布式表引擎 (`Distributed`) |
| **Redis 分片** | 不得改变股票池分片算法 (`xxHash64`) |
| **Async Safety** | 所有共享组件必须是 async-safe (使用 `asyncio.Lock()`) |
| **向后兼容** | 迁移期间旧表名必须继续工作 |
| **测试框架** | 使用 Pytest + Docker (`docker compose -f docker-compose.dev.yml run --rm`) |

---

## Technical Specifications

### 1. Unified API Strategy

**mootdx-api Endpoint**: `/api/v1/tick/{code}`

| 场景 | Parameters | 说明 |
|------|-----------|------|
| 盘中实时 | 无参数 | 默认返回当天最新数据 |
| 盘后当天 | 无参数 | 同上 |
| 盘后历史 | `date=YYYYMMDD` (int) | 返回指定日期数据 |

**Stock Code Cleaning (Crucial)**: 
All components MUST use the following logic to sanitize stock codes:
```python
def clean_stock_code(code: str) -> str:
    # Remove 'sh', 'sz' prefixes (case insensitive) and any dots
    return code.lower().lstrip('sh').lstrip('sz').lstrip('.')
```

---

### 2. Shared Library Design

**Module Path**: `libs/gsd-shared/gsd_shared/tick/`

**Components**:

#### 2.1 TickFetcher
```python
class TickFetcher:
    class Mode(Enum):
        REALTIME = "realtime"      # 单次请求，速度优先
        HISTORICAL = "historical"   # 矩阵搜索，完整性优先
    
    async def fetch(
        self, 
        stock_code: str, 
        trade_date: Optional[str] = None  # None=当天, YYYYMMDD=历史
    ) -> List[Dict]:
        """统一采集接口"""
```

#### 2.2 TickDeduplicator
```python
class TickDeduplicator:
    """基于 (time, price, volume) 元组去重"""
    def __init__(self, cache_size: int = 1500):
        self.cache: Dict[str, deque] = {}
    
    def is_duplicate(self, code: str, item: Dict) -> bool:
        key = f"{item['time']}|{item['price']}|{item.get('vol', item.get('volume'))}"
        # ... 去重逻辑
```

#### 2.3 TickWriter
```python
class TickWriter:
    class Target(Enum):
        INTRADAY_LOCAL = "tick_data_intraday_local"
        INTRADAY_DIST = "tick_data_intraday"
        HISTORY_DIST = "tick_data"
    
    async def write(
        self, 
        stock_code: str, 
        trade_date: str, 
        data: List[Dict]
    ) -> int:
        """
        自动路由写入目标：
        - trade_date == today: 写入 INTRADAY
        - trade_date < today: 写入 HISTORY
        """
```

**字段映射规范**:
```python
# Direction 字段
# API 可能返回: "BUY"/"SELL"/"NEUTRAL" 或 0/1/2
def map_direction(value) -> int:
    if isinstance(value, str):
        return {"BUY": 0, "SELL": 1, "NEUTRAL": 2}.get(value, 2)
    return int(value) if value in [0, 1, 2] else 2

# Volume 字段 (处理 vol/volume 别名)
volume = int(item.get('volume', item.get('vol', 0)))
```

---

### 3. Database Schema Standardization

| 用途 | 分布式表 | 本地表 (新) | 原本地表 (待废弃) |
|------|---------|------------|------------------|
| 当日数据 | `tick_data_intraday` | `tick_data_intraday_local` | `stock_tick_data_local` |
| 历史数据 | `tick_data` | `tick_data_local` | `tick_data_local` (无变化) |

---

## Execution Workflow

### Phase 0: Emergency Fix (P0 - 立即执行)

**目标**: 修复 P1 阻塞性 Bug

| 步骤 | 文件 | 变更 |
|------|------|------|
| 1 | `services/get-stockdata/src/core/collector/components/tick_worker.py:125` | `url = f"{self.mootdx_api_url}/api/v1/tick/{code}"` |

**验证**:
```bash
docker logs intraday-tick-collector 2>&1 | grep -E "tick.*200" | head -5
```

---

### Phase 1: Establish Shared Core (3天)

**目标**: 创建 `gsd_shared.tick` 模块

| 步骤 | 任务 | 输出文件 |
|------|------|---------|
| 1 | 创建模块结构 | `libs/gsd-shared/gsd_shared/tick/__init__.py` |
| 2 | 实现 TickFetcher | `libs/gsd-shared/gsd_shared/tick/fetcher.py` |
| 3 | 实现 TickWriter | `libs/gsd-shared/gsd_shared/tick/writer.py` |
| 4 | 实现 TickDeduplicator | `libs/gsd-shared/gsd_shared/tick/deduplicator.py` |
| 5 | 添加常量 | `libs/gsd-shared/gsd_shared/tick/constants.py` |
| 6 | 编写单元测试 | `libs/gsd-shared/tests/test_tick_*.py` |

**Testing Requirements**:
```bash
cd libs/gsd-shared
pytest tests/test_tick_fetcher.py -v
pytest tests/test_tick_writer.py -v
```

### Phase 2: Refactor Services (2天)

#### 2.1 迁移 gsd-worker

| 文件 | 变更 |
|------|------|
| `services/gsd-worker/src/core/tick_sync_service.py` | 使用 `from gsd_shared.tick import TickFetcher, TickWriter` |
| `services/gsd-worker/src/core/tick_fetcher.py` | **删除** (迁移至共享库) |
| `services/gsd-worker/src/core/tick_writer.py` | **删除** (迁移至共享库) |

#### 2.2 迁移 get-stockdata

| 文件 | 变更 |
|------|------|
| `services/get-stockdata/src/core/collector/components/tick_worker.py` | 使用共享 `TickFetcher` 和代码清洗逻辑 |
| `services/get-stockdata/src/core/collector/components/writer.py` | 保留 (或逐步迁移至共享 TickWriter) |

---

### Phase 3: Schema Migration (1天)

**ClickHouse DDL**:
```sql
-- 创建新本地表 (在所有节点执行)
CREATE TABLE tick_data_intraday_local AS stock_tick_data_local;

-- 更新分布式表定义
ALTER TABLE tick_data_intraday MODIFY SETTING distributed_product_mode = 'local';

-- 数据迁移 (可选，当日数据可直接丢弃)
INSERT INTO tick_data_intraday_local SELECT * FROM stock_tick_data_local;
```

---

### Phase 4: Cleanup (1天)

1. 验证新表数据完整性
2. 删除旧表 `DROP TABLE stock_tick_data_local`
3. 更新所有文档中的表名引用

---

## Definition of Done

| 标准 | 验证方法 |
|------|---------|
| ✅ 所有场景使用相同 Fetcher | `grep -r "TickFetcher" services/` |
| ✅ API 路径统一 | `grep -r "/api/v1/tick" services/` (无 `/ticks`) |
| ✅ 表命名规范 | `clickhouse-client -q "SHOW TABLES LIKE '%tick%'"` |
| ✅ 股票代码格式统一 | 验证入库数据均为无前缀的纯数字 (e.g. "600519") |
| ✅ 单元测试通过 | `pytest libs/gsd-shared/tests/ -v` |

---

## Rollback Plan

| Phase | 回滚步骤 |
|-------|---------|
| Phase 0 | 恢复原 API 路径 (git revert) |
| Phase 2 | 保留旧 Fetcher/Writer 文件，暂不删除 |
| Phase 3 | 保留 `stock_tick_data_local` 表 1 周 |
