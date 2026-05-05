# EPIC: 全量数据源切转与底层纯净 API 提供层重构

## 1. EPIC 概述
- **背景**: 当前 41 服务器的 `get-stockdata` 微服务由于历史原因，部分低频静态及财务数据依旧在即时调用外部 API 或过时的 gRPC 通道。而腾讯云 MySQL 数据底座已搭建完成并可通过单独的采集线保障数据沉淀。
- **架构决策与核心认知**:
  1. **外部 API 仅限采集使用**：云端的 `8001-8003` (BaoStock/Akshare等) 为采集专用代理代理，供内部爬虫后台清洗入库使用。**下游策略查询禁止直接调用，彻底阻断其网络投射**。
  2. **腾讯云 MySQL 作为唯一真实数据源 (SSOT)**：所有清洗后的数据汇聚在腾讯云 MySQL 数据库（含博弈、股东、估值、舆情等表），它是策略分析的核心数据资产。
  3. **41 服务器职责隔离与回归**：41 服务器彻底剥离并停止执行任何由于采集引起的向外网发出的请求动作或写入动作。41 节点的唯一身份是：**量化策略调用网关**，通过建立与腾讯云 MySQL 的只读连接（使用原生 `aiomysql`），按需组装各类指标对外提供高可用 API。
- **目标**: 将 41 服务器 `get-stockdata` 中的财务、估值、排行、资金明细等所有低频/静态路由对应的获取逻辑，彻底从 gRPC 剥离，完全切入 MySQL DAO 层直连。
- **负责人**: 后端研发组
- **验收准则 (DoD)**:
  1. 系统内标定为"迁移类"的存量路由，已彻底断开向外部的第三方 API 透传以及陈旧的 gRPC 直接依赖。
  2. 新编写的 DAO 层使用 `aiomysql` 异步高效直连腾讯云 MySQL 节点数据库。
  3. 各历史维度回测时，新版接口提供的数据结构必须准确适配原量化策略管线的计算逻辑。
- **业务不干涉准则 (Critical Safeguards)**:
  - **实时采集保护**: 本次重构严禁触动盘中实时 Tick 与快照 (Snapshot) 的采集逻辑。现有写入 ClickHouse 的 `src/core/collector/` 模块必须保持逻辑隔离。
  - **热部署安全**: 修改 `main.py` 及公用 DAO 组件时，需确保 gRPC 实时通道的初始化流程（`grpc_client`）优先保障，防止因 MySQL 连接问题导致整个服务崩溃或实时链路中断。

---

## 2. 路由梳理及迁移清单

实施前必须明确每个路由文件的归属，以及其对应的腾讯云 MySQL 表。

### 2.1 需执行迁移的路由（MySQL 只读 DAO 化）

| 路由文件 | 涉及接口 | 现有底层调用 | 适用之新底层 DAO / 表资源 |
|---|---|---|---|
| `valuation_routes.py` | `/valuation/{code}` | gRPC → mootdx-source | `ValuationDAO` 读取 `daily_basic` 表 |
| `market_routes.py` | `/ranking`, `/sector/*`, `/dragon_tiger` | gRPC → mootdx-source | `SectorDAO` 读取 `stock_sector_*`，`DragonTigerDAO` 读取 `stock_lhb_daily` |
| `stocks_routes.py` | `/stocks/list`, `/stocks/{code}/info` | gRPC → mootdx-source | `StockBasicDAO` 读取 `stock_basic_info` |
| `finance_routes.py` | `/finance/indicators/{code}` | gRPC → mootdx-source | `FinanceDAO` 待腾讯云对应表 (`stock_finance_...`) 就绪后读取 |
| `health_routes.py` 等 | / | / | （部分与核心数据查询无关，保持稳定） |

### 2.2 需从 41 节点剥离的写入型路由（严格清除）

| 路由文件 | 当前行为 | 处置方案 |
|---|---|---|
| `sync_routes.py` | 在 41 节点以后台任务执行本地采集与同步。 | 移除核心执行逻辑，将数据收集功能移交给非 41 节点的 `gsd-worker` 承担。41仅保留只读监控。 |
| `repair_routes.py`| 发起远端采集触发机制。 | 迁移操作节点，41服务器限制所有写入与远端更新调用接口。 |

### 2.3 必须保留的原通道路由（高频数据）

| 路由文件 | 涉及接口 | 保留理由 |
|---|---|---|
| `quotes_routes.py` | `/realtime`, `/tick/{code}` | 毫秒级极速盘口交易数据，必须直达专用源 `mootdx`。 |
| `quotes_routes.py` | `/history/{code}` | **已完成迁移**：已具备 ClickHouse 与 MySQL 降级连接链路，无需重构。 |
| `liquidity_routes.py`| `/stocks/{code}/liquidity` | 强依赖实施行情的衍生实时计算。 |

---

## 2.4 实时采集任务安全区 (Real-time Protected Zone)
为实现“不停机、不干涉、不降级”，系统将以下模块划定为“安全保护区”：
1. **逻辑层**: `src/core/collector/` (Tick/快照采集核心)。
2. **连接层**: `src/grpc_client/` (实时行情透传通道)。
3. **存储层**: ClickHouse 连接池 (`ClickHousePoolManager`)。
本 EPIC 下的所有 DAO 扩展及路由重构动作均不得改变上述模块的内部状态。

---

## 3. 既有基础设施及技术栈限制

| 参考项 | 说明及约束 |
|---|---|
| **技术栈约定** | 前置要求使用 `aiomysql` 的异步连接池以及基于此手写的 DAO 层模式。**彻底避免引入 SQLAlchemy 等重型 ORM 框架以保证查询绝对可控与高效执行**。 |
| **复用机制** | 代码已存在的 `MySQLPoolManager` (`src/data_access/mysql_pool.py`) 和 `KLineDAO` 是标准的实施模板，后续模块全部效仿此组件模式编写。 |
| **键名处理规则** | 新增的 DAO 内部需包揽对前端标准的 6 位纯数字 `code` 至存量库表（如含缀的 `ts_code`）的数据结构自动化转化。 |

---

## 4. 实施阶段规划 (STORIES)

### STORY 1: 物理隔离审计确认及 41 节点 DAO 层构建设计 (Schema Map & DAO Init)
- **描述**: 基于现量产的腾讯云结构表集进行确认，建立各分类的 DAO 操作层骨架。
- **实施拆解**:
  1. 通过现有连接确认可直接复用的数据表：`stock_basic_info`, `daily_basic`, `stock_sector_ths`, `stock_sector_cons_ths`, `stock_lhb_daily`，`stock_north_funds_daily`。
  2. 在 `src/data_access/` 中建立以业务类型划分的底层读数据获取类，如：`stock_basic_dao.py`, `valuation_dao.py`, `sector_dao.py`, `dragon_tiger_dao.py` 等。
  3. 为财务数据、资本流向等目前正准备创建或尚未对接全量数据的底层指标规划待用的 `FinanceDAO`、`CapitalFlowDAO`，实施容错降级保证运行时可用。

### STORY 2: 后备库表建设及采集任务节点下放 (Backend Ingestion Handover)
- **描述**: 对非 41 服务器的数据爬取与数据刷新工作作清晰交接验证。
- **实施拆解**:
  1. 将负责主动采集（使用云端 `8001/8002/8003` 代理服务拉取数据）的 `sync` 系列作业，统一部署并调度于诸如 58/111 节点上的后台任务线程 (Task Orchestrator)。
  2. 确立数据表从源头落库直至能被 41 服务器正常选取的监控流水线是畅通无阻的。

### STORY 3: API 服务路由"换芯"及数据拼装层纯净改造 (API Purge)
- **描述**: 切断老旧的提取依赖链条并在内部平稳切换。
- **实施拆解**:
  1. 升级 `finance_routes.py`、`valuation_routes.py`、`market_routes.py` 及 `stocks_routes.py` 等组件文件。
  2. 将请求的底层数据提取器自 `[grpc_client -> mootdx-source]` 平滑交接至 `[data_access -> xxx_DAO.py]`。
  3. 执行 `Depends(get_pool)` 传入 MySQL 的安全连接进程并在前端保持响应协议的强一致兼容。

### STORY 4: 仿真测试、数据对比检验与灰度释放 (Integration & Simulation)
- **描述**: 完成数据接口换路后的大面积正确性回滚检测工作。
- **实施拆解**:
  1. 单一股票切片的数据比对：使用最新的 API 读取响应和老旧的数据源提取的数据（或者源端测试的数据包）相互交叉做严格的值和类型的 DIFF 验证。
  2. 接口端吞吐连通性检验：使用自动发压或连通性监测脚本持续检验 41 节点查询数据的阻塞情况及其容错响应边界。
