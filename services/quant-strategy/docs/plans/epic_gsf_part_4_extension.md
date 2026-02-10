# EPIC-GSF Part 4: 通用扩展 (Tick DAO + Strategy Registry)

**父文档**: [epic_gsf_master.md](./epic_gsf_master.md)  
**状态**: 📝 规划中

---

## 1. 目标

扩展框架以支持 Tick 级别策略 (OFI, VPIN, Lead-Lag)，并实现策略注册机制。

---

## 2. User Stories

### Story 4.1: TickDAO 实现
- **描述**: 封装 Tick 数据的访问逻辑
- **接口**:
  ```python
  class ITickDAO(Protocol):
      async def get_ticks(self, code: str, date: date) -> pd.DataFrame
  ```
- **数据源**: ClickHouse `stock_data.tick_data`
- **验收标准**: 能获取单日完整 Tick 数据

### Story 4.2: FeatureDAO 实现
- **描述**: 封装特征矩阵的访问逻辑
- **接口**:
  ```python
  class IFeatureDAO(Protocol):
      async def get_features(self, code: str, date: date) -> np.ndarray
  ```
- **数据源**: ClickHouse / FeatureStore
- **验收标准**: 能获取 9 维特征矩阵

### Story 4.3: Strategy Registry 实现
- **描述**: 策略注册表，支持动态注册和路由
- **接口**:
  ```python
  class StrategyRegistry:
      def register(self, name: str, engine: IEngine) -> None
      def get(self, name: str) -> IEngine
      def list_strategies(self) -> List[str]
  ```
- **验收标准**: 能动态注册新策略并通过名称获取

### Story 4.4: IEngine 抽象接口
- **描述**: 所有引擎的统一接口
- **接口**:
  ```python
  class IEngine(Protocol):
      async def run(self, target: str, **kwargs) -> Report
  ```
- **验收标准**: SubNewBenchmarkEngine 和 LeadLagEngine 均实现该接口

---

## 3. 文件结构

```
quant-strategy/src/
├── dao/
│   ├── tick_dao.py        # [NEW]
│   └── feature_dao.py     # [NEW]
├── engines/
│   ├── interfaces.py      # IEngine [NEW]
│   └── lead_lag_engine.py # [FUTURE]
└── registry/
    └── strategy_registry.py # [NEW]
```

---

## 4. 后续扩展

完成 Part 4 后，框架将支持：
- OFI 实时订单失衡分析
- VPIN 知情交易概率监控
- Lead-Lag 龙头跟随识别
- Smart Money 大单资金追踪
