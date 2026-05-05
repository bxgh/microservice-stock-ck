# quant-strategy 服务规格说明

> **版本**: v1.0  
> **更新时间**: 2026-01-17  
> **服务端口**: 8084  
> **状态**: 🔄 开发中

---

## 1. 服务概述

`quant-strategy` 是量化策略引擎微服务，提供策略管理、信号生成与回测功能，支持多种 A 股日内交易策略。

### 1.1 核心职责

| 职责 | 描述 |
|------|------|
| 策略管理 | 策略的 CRUD 操作 |
| 信号生成 | 基于实时/历史数据生成交易信号 |
| 回测引擎 | 历史数据回测验证 |
| 风险控制 | 仓位限制、止损止盈 |

### 1.2 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI (Uvicorn) |
| 计算引擎 | Pandas + Numpy (向量化) |
| 数据库 | SQLite (策略存储) |
| 缓存 | Redis (信号缓存) |
| 服务注册 | Nacos (可选) |

---

## 2. 支持策略

### 2.1 策略清单

| 代码 | 名称 | 描述 | 状态 |
|------|------|------|------|
| `ofi` | 订单流失衡策略 | 基于 Order Flow Imbalance 分析多空力量 | 🔄 开发中 |
| `smart_money` | 大单资金追踪 | 识别主力资金吸筹/出货行为 | 🔄 开发中 |
| `order_book` | 盘口压力分析 | 分析五档盘口的委买委卖压力差 | 🔄 开发中 |
| `vwap` | VWAP 乖离策略 | 基于 VWAP 的均值回归/趋势确认 | 🔄 开发中 |
| `liquidity_shock` | 流动性冲击监控 | 监测交易对价格的冲击成本 | 🔄 开发中 |

---

### 2.2 OFI 策略详情

**订单流失衡策略 (Order Flow Imbalance)**

**原理**:
- 计算主动买单与主动卖单的数量差异
- 失衡达到阈值时产生信号

**计算公式**:
```
OFI = Σ(主动买量) - Σ(主动卖量)
OFI_Ratio = OFI / (主动买量 + 主动卖量)
```

**信号逻辑**:
| 条件 | 信号 | 强度 |
|------|------|------|
| OFI_Ratio > 0.3 | BUY | Strong |
| OFI_Ratio > 0.1 | BUY | Weak |
| OFI_Ratio < -0.3 | SELL | Strong |
| OFI_Ratio < -0.1 | SELL | Weak |

---

### 2.3 Smart Money 策略详情

**大单资金流向追踪**

**原理**:
- 识别超过阈值的大单交易
- 追踪大单的买卖方向和资金流入流出

**大单判定**:
```
大单阈值 = 当日平均成交量 × 系数 (默认 5)
```

**信号逻辑**:
| 条件 | 信号 |
|------|------|
| 大单净流入 > 阈值 | 主力吸筹 → BUY |
| 大单净流出 > 阈值 | 主力出货 → SELL |

---

### 2.4 VWAP 策略详情

**日内加权均价乖离策略**

**VWAP 计算**:
```
VWAP = Σ(成交价 × 成交量) / Σ(成交量)
乖离率 = (现价 - VWAP) / VWAP × 100%
```

**信号逻辑**:
| 条件 | 策略 | 信号 |
|------|------|------|
| 乖离率 < -2% | 均值回归 | BUY |
| 乖离率 > 2% | 均值回归 | SELL |
| 乖离率 > 1% 且持续上升 | 趋势跟随 | BUY |

---

## 3. API 接口规格

### 3.1 策略管理

#### 获取策略列表

```
GET /api/v1/strategies/
```

**响应**:
```json
{
  "strategies": [
    {
      "id": "strategy_001",
      "type": "ofi",
      "name": "OFI主力追踪",
      "enabled": true,
      "created_at": "2026-01-15T10:00:00"
    }
  ]
}
```

---

#### 获取策略详情

```
GET /api/v1/strategies/{id}
```

---

#### 创建策略

```
POST /api/v1/strategies/
```

**请求体**:
```json
{
  "type": "ofi",
  "name": "OFI主力追踪",
  "params": {
    "threshold": 0.3,
    "window": 60
  },
  "stocks": ["600519", "000001"],
  "enabled": true
}
```

---

#### 启用/禁用策略

```
PUT /api/v1/strategies/{id}/toggle
```

---

#### 删除策略

```
DELETE /api/v1/strategies/{id}
```

---

### 3.2 信号查询

#### 获取策略信号

```
GET /api/v1/strategies/{id}/signals?date={YYYYMMDD}&limit={n}
```

**响应**:
```json
{
  "signals": [
    {
      "stock_code": "600519",
      "direction": "BUY",
      "strength": 0.85,
      "price": 1850.00,
      "timestamp": "2026-01-17T14:30:00",
      "reason": "OFI_Ratio=0.42, 超过阈值0.3"
    }
  ]
}
```

---

### 3.3 回测接口

#### 执行回测

```
POST /api/v1/strategies/{id}/backtest
```

**请求体**:
```json
{
  "start_date": "2025-12-01",
  "end_date": "2026-01-15",
  "initial_capital": 1000000,
  "max_position_per_stock": 0.1
}
```

**响应**:
```json
{
  "total_return": 0.125,
  "annualized_return": 0.58,
  "max_drawdown": 0.082,
  "sharpe_ratio": 1.85,
  "win_rate": 0.62,
  "trade_count": 48,
  "equity_curve": [...]
}
```

---

### 3.4 健康检查

```
GET /api/v1/health
GET /api/v1/ready
GET /api/v1/live
```

---

## 4. 信号数据结构

### 4.1 信号模型

```python
class Signal(BaseModel):
    stock_code: str     # 股票代码
    direction: str      # BUY / SELL / HOLD
    strength: float     # 信号强度 (0-1)
    price: float        # 触发价格
    timestamp: datetime # 触发时间
    reason: str         # 触发原因
    strategy_id: str    # 策略ID
    meta: dict          # 额外元数据
```

### 4.2 信号强度

| 强度 | 范围 | 含义 |
|------|------|------|
| Strong | 0.7 - 1.0 | 强信号，建议立即执行 |
| Medium | 0.4 - 0.7 | 中等信号，可择机执行 |
| Weak | 0.0 - 0.4 | 弱信号，仅供参考 |

---

## 5. 核心组件

### 5.1 策略引擎

**目录**: `src/strategies/`

| 模块 | 说明 |
|------|------|
| `base_strategy.py` | 策略基类 |
| `ofi_strategy.py` | OFI 策略实现 |
| `smart_money_strategy.py` | Smart Money 策略 |
| `vwap_strategy.py` | VWAP 策略 |
| `order_book_strategy.py` | 盘口压力策略 |
| `liquidity_shock_strategy.py` | 流动性冲击策略 |

---

### 5.2 回测引擎

**目录**: `src/backtest/`

| 模块 | 说明 |
|------|------|
| `engine.py` | 回测核心引擎 |
| `data_loader.py` | 历史数据加载 |
| `performance.py` | 绩效计算 |

---

### 5.3 数据适配器

**目录**: `src/adapters/`

| 模块 | 说明 |
|------|------|
| `stockdata_adapter.py` | get-stockdata 数据源适配 |
| `redis_adapter.py` | Redis 实时数据适配 |

---

## 6. 配置

### 6.1 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `QS_PORT` | 8084 | 服务端口 |
| `QS_LOG_LEVEL` | INFO | 日志级别 |
| `QS_STOCKDATA_SERVICE_URL` | http://get-stockdata:8080 | 数据源服务地址 |
| `QS_MAX_CONCURRENT_STRATEGIES` | 20 | 最大并发策略数 |
| `QS_REDIS_HOST` | 127.0.0.1 | Redis 地址 |
| `QS_REDIS_PORT` | 6379 | Redis 端口 |
| `NACOS_SERVER_ADDR` | - | Nacos 服务地址 (可选) |

### 6.2 策略配置

**文件**: `config/quant-strategy.yaml`

```yaml
strategies:
  ofi:
    default_threshold: 0.3
    window_seconds: 60
    
  smart_money:
    large_order_multiplier: 5
    
  vwap:
    deviation_threshold: 0.02
    
risk:
  max_single_stock_loss: 0.02    # 单股最大亏损 2%
  total_drawdown_limit: 0.15      # 总回撤限制 15%
```

---

## 7. 风险控制

### 7.1 仓位限制

| 限制 | 参数 | 默认值 |
|------|------|--------|
| 单股最大持仓 | `max_position_per_stock` | 10% |
| 单日交易次数 | `max_trades_per_day` | 10 |
| 总持仓上限 | `max_total_position` | 80% |

### 7.2 止损止盈

| 类型 | 参数 | 默认值 |
|------|------|--------|
| 单股止损 | `stop_loss` | -2% |
| 单股止盈 | `take_profit` | 5% |
| 总账户止损 | `total_drawdown_limit` | -15% |

---

## 8. 计算规范

### 8.1 向量化要求

- **必须使用** Numpy/Pandas 向量化操作
- **禁止使用** Python 原生循环处理数值数据
- **延迟目标**: 信号生成 < 100ms

### 8.2 滑动窗口

```python
from collections import deque

# 使用 deque 实现固定大小滑动窗口
tick_window = deque(maxlen=1800)  # 30分钟数据
```

### 8.3 内存限制

- 每只股票最多保留 30 分钟 Tick 数据
- 历史数据按需加载，不常驻内存

---

## 9. 部署

### 9.1 Docker 运行

```bash
docker build -t quant-strategy:latest .
docker run -p 8084:8084 \
  -e QS_STOCKDATA_SERVICE_URL=http://host.docker.internal:8080 \
  quant-strategy
```

### 9.2 Docker Compose

```bash
cd services/quant-strategy
docker-compose up -d
```

### 9.3 本地开发

```bash
cd services/quant-strategy
pip install -r requirements.txt
python src/main.py
```

---

## 10. API 文档

访问 Swagger UI: `http://localhost:8084/docs`

---

## 11. 依赖服务

| 服务 | 用途 | 必需 |
|------|------|------|
| get-stockdata / gsd-api | 行情数据 | ✅ |
| Redis | 信号缓存 | ❌ |
| Nacos | 服务注册 | ❌ |

---

## 12. 后续开发计划

- [ ] 实现 OFI 策略计算引擎
- [ ] 实现 Smart Money 资金流向分析
- [ ] 实现盘口压力实时监控
- [ ] 实现 VWAP 计算与信号生成
- [ ] 实现流动性冲击检测
- [ ] 完善回测框架
- [ ] 添加 WebSocket 实时推送

---

## 13. 相关文档

| 文档 | 路径 |
|------|------|
| 策略设计文档 | `docs/design/stratege/` |
| 测试用例 | `tests/` |
