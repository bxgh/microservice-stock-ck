# EPIC-GSF Part 1: DAO Layer 基础设施

**父文档**: [epic_gsf_master.md](./epic_gsf_master.md)  
**状态**: 📝 规划中  
**架构决策**: 集中式 (Option A) - 所有数据通过 mootdx-source gRPC 获取

---

## 1. 目标

构建数据访问层 (DAO Layer)，作为 `mootdx-source` gRPC 服务的客户端封装，为上层分析器提供统一的数据接口。

> **架构约束**: 所有 DAO 实现**不得**直接访问 MySQL/ClickHouse，必须通过 gRPC 调用 `mootdx-source`。

---

## 2. User Stories

### Story 1.1: DataSourceClient gRPC 客户端
- **描述**: 封装 `mootdx-source` 的 gRPC 调用逻辑
- **接口**:
  ```python
  class DataSourceClient:
      async def fetch(self, data_type: DataType, codes: List[str], params: Dict) -> pd.DataFrame
  ```
- **依赖**: grpcio-tools, protobuf
- **验收标准**: 能对 mootdx-source 发起 FetchData 请求

### Story 1.2: StockInfoDAO 实现
- **描述**: 封装 `DATA_TYPE_ISSUE_PRICE` 和 `DATA_TYPE_META` 的访问逻辑
- **接口**:
  ```python
  class IStockInfoDAO(Protocol):
      async def get_stock_info(self, code: str) -> StockInfo
      async def get_issue_price(self, code: str) -> Decimal
      async def get_listing_date(self, code: str) -> date
  ```
- **数据源**: mootdx-source gRPC (DATA_TYPE_ISSUE_PRICE, DATA_TYPE_META)
- **验收标准**: 能成功获取 688802 的 issue_price 和 list_date

### Story 1.3: IndustryDAO 实现
- **描述**: 封装 `DATA_TYPE_SW_INDUSTRY` 的访问逻辑
- **接口**:
  ```python
  class IIndustryDAO(Protocol):
      async def get_industry(self, code: str, level: int = 2) -> str
      async def get_industry_tree(self, code: str) -> IndustryTree
  ```
- **数据源**: mootdx-source gRPC (DATA_TYPE_SW_INDUSTRY)
- **验收标准**: 能获取 000001.SZ 的 L1/L2/L3 三级行业

### Story 1.4: KLineDAO 实现
- **描述**: 封装 `DATA_TYPE_HISTORY` 的访问逻辑
- **接口**:
  ```python
  class IKLineDAO(Protocol):
      async def get_kline(self, code: str, start: date, end: date) -> pd.DataFrame
  ```
- **数据源**: mootdx-source gRPC (DATA_TYPE_HISTORY)
- **验收标准**: 能获取 688802 自上市日至今的完整 K 线

### Story 1.5: PeerSelector 实现
- **描述**: 基于 StockInfoDAO 和 IndustryDAO 筛选同类股
- **逻辑**: 市场板块 + 申万行业 + 上市时间窗口
- **验收标准**: 能为 688802 筛选出 >= 3 支同类股

---

## 3. 技术规范

- **异步优先**: 所有 DAO 方法必须使用 `async/await`
- **连接池**: 使用 `aiomysql` 连接池
- **错误处理**: 数据不存在时抛出 `DataNotFoundError`

---

## 4. 文件结构

```
quant-strategy/src/dao/
├── __init__.py
├── interfaces.py         # IStockInfoDAO, IKLineDAO 等接口定义
├── stock_info_dao.py     # StockInfoDAO 实现
├── industry_dao.py       # IndustryDAO 实现
├── kline_dao.py          # KLineDAO 实现
└── peer_selector.py      # PeerSelector 实现
```
