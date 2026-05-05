# CCI Monitor · 技术规范速查 v2

> 本文档是 `CCI_Monitor_Epic_Stories.md` (v2) 的技术速查版。
> 专用于 AI coding agent 在编写代码时快速查询实现细节。
> **v2 升级:** 新增完整系统形态(数据库、API、前端)的技术规范。

---

## 📐 核心数学公式

### CCI 合成指数

```
CCI = α + β + γ + δ

α = 0.4 × (ρ̄_market / 0.5)              权重 40% · 市场级相关性
β = 0.3 × max(ρ̄_resonant / ρ̄_deep, 1)   权重 30% · 介质反转
γ = 0.2 × max(Δρ̄ / 0.15, 0)             权重 20% · 斜率变化
δ = 0.1 × max(ρ̄_down / ρ̄_up, 1)         权重 10% · 方向分解
```

### 四条信号

**信号①波动率比:**
```
σ_short = std(returns[t-20:t]) × sqrt(252)
σ_long  = std(returns[t-60:t]) × sqrt(252)
ratio   = σ_short / σ_long
triggered = (ratio > 1.5 for 5 consecutive days)
```

**信号②自相关:**
```
AR1(t) = Corr(returns[t-60:t], shift(returns[t-60:t], 1))
triggered = AR1 > 0.15
```

**信号③偏度:**
```
skew = scipy.stats.skew(returns[t-60:t])
skew_change = skew(t) - skew(t-20)
triggered = |skew| > 1.0 OR |skew_change| > 1.5
```

**信号④横截面相关性(核心):**
```
# 对时刻 t, N 只股票在过去 20 日的收益率矩阵 R (20×N)
# 计算 N×N 相关矩阵,取上三角(不含对角)均值
ρ̄(t) = mean( Corr(R)[i,j] for i < j )
```

### 预警分级

```python
def classify(cci: float) -> tuple[int, str]:
    if cci < 0.7:  return 0, "安全"      # 🟢
    if cci < 1.0:  return 1, "关注"      # 🟡
    if cci < 1.3:  return 2, "警戒"      # 🟠
    else:          return 3, "临界"      # 🔴
```

---

## 🏗️ 关键数据结构

### Pydantic 模型

```python
from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Literal

class DailyBar(BaseModel):
    date: date
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    change_pct: float
    
    @field_validator("high")
    @classmethod
    def high_ge_low(cls, v, info):
        if "low" in info.data and v < info.data["low"]:
            raise ValueError("high must >= low")
        return v

class CCIResult(BaseModel):
    date: date
    layer_id: int = Field(ge=1, le=6)
    
    cci: float
    alpha: float
    beta: float
    gamma: float
    delta: float
    
    alert_level: int = Field(ge=0, le=3)
    alert_label: Literal["安全", "关注", "警戒", "临界"]
    
    market_rho: float
    resonant_rho: float | None = None
    deep_rho: float | None = None
    delta_rho: float | None = None
    up_down_ratio: float | None = None
    
    computed_at: datetime
    data_as_of: date

class DislocationEvent(BaseModel):
    date: date
    type: Literal["iceberg", "false_alarm", "inversion", "leader_lag"]
    severity: int = Field(ge=1, le=5)
    involved_layers: list[int]
    description: str
```

### SQLAlchemy ORM 模型

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, Integer, Date, DateTime, JSON, Boolean, UniqueConstraint, Index

class CCIRecord(Base):
    __tablename__ = "cci_records"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    layer_id: Mapped[int] = mapped_column(Integer, index=True)
    
    cci: Mapped[float]
    alpha: Mapped[float]
    beta: Mapped[float]
    gamma: Mapped[float]
    delta: Mapped[float]
    
    alert_level: Mapped[int]
    alert_label: Mapped[str] = mapped_column(String(20))
    
    market_rho: Mapped[float | None]
    resonant_rho: Mapped[float | None]
    deep_rho: Mapped[float | None]
    delta_rho: Mapped[float | None]
    up_down_ratio: Mapped[float | None]
    
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    computed_at: Mapped[datetime]
    
    __table_args__ = (
        UniqueConstraint("date", "layer_id", name="uq_date_layer"),
        Index("ix_date_layer", "date", "layer_id"),
    )
```

---

## 🔌 数据源接口规范 (MySQL API)

> **详细参考**: [data-layer.md](file:///home/bxgh/microservice-stock/docs/CCI_monitor/data-layer.md)

### 核心接口映射

| 数据需求 | 内部 API 路径 | 说明 |
|---|---|---|
| **指数行情** | `/api/v1/quotes/history/{symbol}` | symbol 如 `sh000300` |
| **个股行情** | `/api/v1/quotes/history/{code}` | code 如 `600519` |
| **成分股列表**| `/api/v1/market/sector/{name}/stocks` | name 如 `沪深300` |

### 调用示例 (Python)

```python
import httpx

async def fetch_api_data(endpoint: str, params: dict):
    base_url = "http://get-stockdata:8083"
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base_url}{endpoint}", params=params)
        return resp.json()
```

### 常见处理逻辑

1. **日期转换**: API 返回 `trade_date` 字符串需转换为 `pd.Timestamp`。
2. **复权处理**: 统一请求 `adjust=2` (后复权) 以保证指标连续性。
3. **空值检查**: 显式检查 `success` 字段和 `data` 长度。

---

## ⚡ 性能关键代码

### 横截面相关性矢量化实现

**不要使用:**
```python
# ❌ 慢!循环中用 pandas.corr()
for t in range(window, T):
    win = returns_wide.iloc[t-window:t]
    corr = win.corr()  # 慢
    result.iloc[t] = corr.values[np.triu_indices_from(corr, k=1)].mean()
```

**必须使用:**
```python
import numpy as np

def compute_rho_bar_fast(returns_matrix: np.ndarray, window: int) -> np.ndarray:
    """
    矢量化实现.
    
    参数:
        returns_matrix: (T, N) 矩阵,每日每股收益率
        window: 滚动窗口
    
    返回:
        (T,) 数组,前 window 个为 NaN
    
    性能: 300 股 × 250 天 < 2 秒
    """
    T, N = returns_matrix.shape
    result = np.full(T, np.nan)
    
    for t in range(window, T):
        win = returns_matrix[t-window:t]  # (window, N)
        
        # 中心化
        mean = np.nanmean(win, axis=0)
        centered = win - mean
        
        # 标准化(注意处理 std=0)
        std = np.nanstd(centered, axis=0)
        valid = std > 1e-10
        if valid.sum() < 10:
            continue
        
        normalized = centered[:, valid] / std[valid]
        
        # 相关矩阵 = 标准化数据的外积 / (window - 1)
        corr = (normalized.T @ normalized) / (window - 1)
        
        # 上三角均值(不含对角)
        n_valid = valid.sum()
        mask = np.triu(np.ones((n_valid, n_valid), dtype=bool), k=1)
        result[t] = np.nanmean(corr[mask])
    
    return result
```

### 进一步优化:增量计算

对于每日增量更新场景,可以仅计算最新一天,而不是重算整个序列。

```python
def compute_rho_bar_incremental(
    returns_matrix: np.ndarray,
    window: int,
    last_computed: np.ndarray | None = None,
) -> np.ndarray:
    """增量计算 - 仅算最新几天."""
    if last_computed is None:
        return compute_rho_bar_fast(returns_matrix, window)
    
    # 只算 last_computed 末尾到现在的差距
    offset = len(last_computed)
    T = len(returns_matrix)
    result = np.full(T, np.nan)
    result[:offset] = last_computed
    
    for t in range(offset, T):
        # ... 同上
    
    return result
```

---

## 🎨 前端主题配置

### TailwindCSS 完整主题(与 Volume XI 对齐)

```typescript
// frontend/tailwind.config.ts
import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // ==== 背景系(深色) ====
        'bg':       '#0a0906',    // 主背景
        'bg-elev':  '#13100b',    // 卡片
        'bg-deep':  '#1a1610',    // 嵌入
        'bg-inner': '#1f1a12',    // 最内层
        
        // ==== 文字(高对比度亮色) ====
        'ink':      '#f2ead8',    // 正文
        'ink-dim':  '#c9bfa8',    // 次要
        'ink-soft': '#8d8575',    // 弱文字
        'muted':    '#5c564a',    // 边框级
        
        // ==== 强调色 ====
        'accent':   '#d65d43',    // 朱砂红
        'accent-2': '#7fbba3',    // 青绿
        'gold':     '#e0b663',    // 金色
        'blue':     '#6fa8d0',    // 靛蓝
        'purple':   '#b88cd0',    // 紫
        
        // ==== 警报色 ====
        'alert-safe':     '#7fbba3',
        'alert-attention':'#e0b663',
        'alert-warning':  '#d65d43',
        'alert-critical': '#e87060',
        
        // ==== 层级色 ====
        'layer-1': '#d65d43',
        'layer-2': '#e0b663',
        'layer-3': '#7fbba3',
        'layer-4': '#6fa8d0',
        'layer-5': '#b88cd0',
        'layer-6': '#8d8575',
        
        // ==== 线条 ====
        'line':      '#332d22',
        'line-soft': '#241f17',
      },
      fontFamily: {
        'serif': ['"Noto Serif SC"', 'serif'],
        'display': ['"Cormorant Garamond"', 'serif'],
        'mono': ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
} satisfies Config
```

### 常用组件样式模板

```tsx
// 统计卡
<div className="bg-bg-elev border border-line border-l-4 border-l-accent p-4">
  <div className="text-xs uppercase tracking-widest text-ink-soft">当前 CCI</div>
  <div className="text-2xl font-mono font-bold text-ink mt-1">1.24</div>
  <div className="text-xs text-ink-dim mt-1">二阶警戒</div>
</div>

// 警报徽章
<span className="inline-block px-2 py-1 text-xs font-mono tracking-wider 
                 bg-alert-warning/15 text-alert-warning border border-alert-warning">
  警戒
</span>
```

### 图表配色常量

```typescript
// src/lib/chartColors.ts
export const CHART_COLORS = {
  primary: '#d65d43',
  secondary: '#e0b663',
  tertiary: '#7fbba3',
  quaternary: '#6fa8d0',
  quinary: '#b88cd0',
  
  grid: '#332d22',
  axis: '#8d8575',
  label: '#c9bfa8',
  
  alert: {
    safe: '#7fbba3',
    attention: '#e0b663',
    warning: '#d65d43',
    critical: '#e87060',
  },
  
  layer: ['#d65d43', '#e0b663', '#7fbba3', '#6fa8d0', '#b88cd0', '#8d8575'],
};
```

---

## 🔗 API 规范

### RESTful 端点清单

| 方法 | 路径 | 请求参数 | 返回 |
|---|---|---|---|
| GET | `/api/v1/cci/latest` | `?layer=1` | `CCIResponse` |
| GET | `/api/v1/cci/history` | `?layer=1&start=...&end=...` | `CCIResponse[]` |
| GET | `/api/v1/layers/latest` | - | `CCIResponse[]` (6 个层级) |
| GET | `/api/v1/layers/{id}/history` | `?days=60` | `CCIResponse[]` |
| GET | `/api/v1/layers/{id}/components` | - | `ComponentInfo[]` |
| GET | `/api/v1/backtest/latest` | - | `BacktestResponse` |
| POST | `/api/v1/backtest/run` | body: `BacktestRequest` | `BacktestResponse` |
| GET | `/api/v1/alerts/recent` | `?limit=20` | `AlertRecord[]` |
| GET | `/api/v1/dislocations/recent` | `?limit=20` | `DislocationEvent[]` |
| GET | `/api/v1/system/health` | - | `HealthResponse` |
| POST | `/api/v1/system/refresh` | body: `{layer?: number}` | `{task_id: string}` |

### 响应格式(Pydantic)

```python
# backend/src/cci_monitor/api/schemas.py

class CCIResponse(BaseModel):
    date: str  # ISO 格式
    layer_id: int
    cci: float
    alpha: float
    beta: float
    gamma: float
    delta: float
    alert_level: int
    alert_label: str
    market_rho: float
    resonant_rho: float | None = None
    deep_rho: float | None = None
    delta_rho: float | None = None
    up_down_ratio: float | None = None
    computed_at: str

class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    data_source: dict  # {"akshare": "healthy", ...}
    database: Literal["healthy", "unhealthy"]
    last_computation: str | None
    uptime_seconds: int

class ErrorResponse(BaseModel):
    error: str  # 错误代码如 "DATA_SOURCE_TIMEOUT"
    message: str
    context: dict | None = None
```

### 错误响应规范

```json
{
  "error": "DATA_SOURCE_TIMEOUT",
  "message": "akshare timeout: fetch_index_daily",
  "context": {
    "symbol": "sh000300",
    "retry_count": 3
  }
}
```

HTTP 状态码:
- `200` 成功
- `400` 业务错误(如数据不足)
- `404` 资源不存在
- `422` 请求参数错误(Pydantic 校验失败)
- `500` 服务器内部错误
- `503` 服务不可用(数据源故障)

---

## 📊 阈值参考表

### 单信号阈值

| 信号 | 关注 | 警戒 | 临界 |
|---|---|---|---|
| ① 波动率比 | > 1.3 | > 1.5 | > 1.8 |
| ② AR(1) | > 0.10 | > 0.15 | > 0.25 |
| ③ 偏度 | \|s\|>0.7 | \|s\|>1.0 | \|s\|>1.5 |
| ④ ρ̄ | > 0.40 | > 0.55 | > 0.65 |

### CCI 综合阈值

| 等级 | CCI 区间 | 颜色 | 建议 |
|---|---|---|---|
| 0 安全 | < 0.7 | 🟢 green | 常规操作 |
| 1 关注 | 0.7-1.0 | 🟡 gold | 暂停加杠杆 |
| 2 警戒 | 1.0-1.3 | 🟠 accent | 开始减仓 |
| 3 临界 | > 1.3 | 🔴 danger | 防御优先 |

### 介质判定

| 介质 | 响应系数 | 代表指数 | 识别规则 |
|---|---|---|---|
| 黏稠 | 0.5× | 中证红利 | 换手率低 + 险资占比高 |
| 深水 | 1.0× | 沪深300 | 机构占比高 + 规模大 |
| 浅水 | 2.0× | 中证2000 | 中小盘 + 量化活跃 |
| 共振 | 2.5× | 万得微盘 | 小市值 + 高杠杆 + 题材 |
| 结冰 | 0.2× | 冷门股 | 流动性枯竭 |

---

## 🧪 测试策略

### 测试分层

| 层级 | 工具 | 运行频率 | 覆盖率要求 |
|---|---|---|---|
| 单元测试 | pytest | 每次 commit | > 80% (核心模块) |
| 集成测试 | pytest + 真实 akshare | 每日 CI | 关键路径 |
| E2E 测试 | Playwright (前端) | 每周 | 主流程 |
| 性能基准 | pytest-benchmark | 每月 | 关键算法 |

### 必写的单元测试

```python
# === 数据层 ===
def test_akshare_fetch_index_daily_success():
    """akshare 成功获取沪深300"""

def test_akshare_fetch_invalid_symbol():
    """无效代码抛出 DataSourceEmptyError"""

def test_cache_hit_returns_cached_data():
    """缓存命中返回缓存数据"""

def test_cache_ttl_expiration():
    """TTL 过期后重新获取"""

# === 信号 ===
def test_variance_rise_constant_returns():
    """常数收益 → 无触发"""

def test_rho_bar_independent_stocks():
    """独立随机序列 → ρ̄ ≈ 0"""

def test_rho_bar_synchronized_stocks():
    """完全同步序列 → ρ̄ ≈ 1"""

def test_rho_bar_performance():
    """300股×250天 < 3秒"""

# === CCI ===
def test_cci_baseline():
    """基准场景 CCI 在 0.5-0.9 间"""

def test_cci_critical():
    """临界场景 CCI > 1.3"""

# === 分层 ===
def test_layer_1_market_computes():
    """L1 能正常输出 CCI"""

def test_dislocation_iceberg_detection():
    """冰山信号能被识别"""
```

---

## 🚨 错误处理规范

```python
from cci_monitor.core.exceptions import (
    DataSourceTimeoutError, 
    DataSourceUnavailableError,
    InsufficientDataError,
)

# 标准模板
async def safe_fetch_index(symbol: str):
    try:
        data = await datasource.fetch_index_daily(symbol, start_date)
    except DataSourceTimeoutError:
        logger.warning(f"{symbol} timeout, using cache")
        data = cache.get_fallback(symbol)
        if data is None:
            raise DataSourceUnavailableError(f"no data for {symbol}")
    except DataSourceError:
        logger.exception(f"data source error for {symbol}")
        raise
    
    if len(data) < 60:
        raise InsufficientDataError(f"only {len(data)} bars, need 60")
    
    return data
```

### 降级策略

**数据源故障时的降级:**
1. 重试 3 次(指数退避)
2. 失败后检查缓存
3. 缓存不可用时使用昨日快照
4. 所有失败时发出健康告警

---

## 📝 日志规范

```python
from loguru import logger

# 正确使用
logger.debug("Fetching {symbol}", symbol="sh000300")
logger.info("CCI computed: {cci} for layer {layer}", cci=0.85, layer=1)
logger.warning("Falling back to cache for {symbol}", symbol="sh000300")
logger.error("Computation failed for layer {layer}", layer=1)
logger.exception("Unexpected error")  # 自动包含 traceback
logger.critical("Database connection lost")
```

### 日志级别

- **DEBUG:** 详细追踪,生产环境关闭
- **INFO:** 关键节点(开始/结束/关键值)
- **WARNING:** 非致命问题(降级、重试)
- **ERROR:** 功能失败但系统继续运行
- **CRITICAL:** 系统级故障(需立即响应)

---

## 🎯 开发优先级(Milestone 速查)

| Milestone | 周数 | 工时 | 核心产出 |
|---|---|---|---|
| M1 地基 | 1-2 | 20-25h | 项目骨架 + 数据层 |
| M2 核心指标 | 2-3 | 20-25h | CCI 能算出并落库 |
| M3 分层+回测 | 4 | 20h | L1-L3 + 回测报告 |
| M4 API | 5 | 15h | REST API + Docker |
| M5 前端 | 6-7 | 30h | 完整 Web 仪表盘 |
| M6 自动化 | 8 | 12h | 调度 + 推送 |

**总计 ≈ 115-130 小时,8 周完成**

---

## 💡 给 AI Agent 的关键提示

### 1. 优先级判断

遇到冲突时的优先级:
- 正确性 > 性能 > 可读性 > 代码量
- 异常处理 > 主流程
- 测试 > 文档

### 2. 代码约定

- **async 优先** — I/O 操作都用 async/await
- **类型完整** — 所有函数签名都有类型注解
- **不信任外部** — akshare 返回的一切都要校验
- **不硬编码** — 任何阈值、URL、路径都从 Settings 读

### 3. 性能敏感代码

以下代码必须使用 numpy 而非 pandas:
- 横截面相关性计算
- 滚动窗口统计
- 批量矩阵运算

### 4. 数据库操作

- 所有写入必须在事务中
- 批量插入使用 `insert().values([...])` 一次性提交
- 读取时使用 `select(Model).where(...)` 新语法(SQLAlchemy 2.0)

### 5. 前端开发

- 所有数据通过 React Query,不在组件中直接 fetch
- TypeScript 严格模式(strict: true)
- 组件拆分原则:单一职责,> 100 行就拆

---

## 🐳 Docker 部署速查

### 本地开发

```bash
# 仅启动 PostgreSQL
docker-compose up -d postgres

# 本地跑 backend
cd backend && uvicorn cci_monitor.api.main:app --reload

# 本地跑 frontend
cd frontend && npm run dev
```

### 生产部署

```bash
# 一键启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend

# 数据库迁移
docker-compose exec backend alembic upgrade head
```

### Caddy 反向代理配置

```caddy
# deploy/caddy/Caddyfile
cci.yourdomain.com {
    # 前端
    handle /* {
        reverse_proxy frontend:3000
    }
    # API
    handle /api/* {
        reverse_proxy backend:8000
    }
    # 健康检查
    handle /health {
        reverse_proxy backend:8000
    }
    # 自动 HTTPS
    tls your@email.com
}
```

---

## 📦 依赖清单

### Backend (pyproject.toml)

```toml
[project]
name = "cci-monitor"
version = "1.0.0"
requires-python = ">=3.11"

dependencies = [
    # 核心
    "pandas >=2.1",
    "numpy >=1.26",
    "scipy >=1.11",
    
    # 数据源
    "akshare >=1.12",
    
    # Web
    "fastapi >=0.109",
    "uvicorn[standard] >=0.25",
    
    # 数据库
    "sqlalchemy >=2.0",
    "asyncpg >=0.29",
    "alembic >=1.13",
    
    # 配置/日志
    "pydantic >=2.5",
    "pydantic-settings >=2.1",
    "loguru >=0.7",
    
    # 调度
    "apscheduler >=3.10",
    
    # 工具
    "tenacity >=8.2",
    "httpx >=0.26",
    "python-multipart",
]

[project.optional-dependencies]
dev = [
    "pytest >=7.4",
    "pytest-asyncio >=0.23",
    "pytest-cov >=4.1",
    "pytest-benchmark >=4.0",
    "ruff >=0.1",
    "mypy >=1.8",
    "types-requests",
]
```

### Frontend (package.json)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.0",
    "@tanstack/react-query": "^5.17.0",
    "zustand": "^4.4.7",
    "axios": "^1.6.5",
    "recharts": "^2.10.4",
    "d3": "^7.8.5",
    "date-fns": "^3.2.0",
    "clsx": "^2.1.0",
    "lucide-react": "^0.309.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.47",
    "@types/d3": "^7.4.3",
    "typescript": "^5.3.3",
    "vite": "^5.0.11",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.33"
  }
}
```

---

**End of Technical Specification v2**
