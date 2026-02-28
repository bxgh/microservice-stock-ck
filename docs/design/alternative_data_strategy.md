# 另类数据策略设计方案：AI 产业链生态遥测

## 1. 中心思想提炼

原文档的核心想法可以用一句话概括：

> **用非行情数据（开源社区活跃度、算力供需、产业采购）的异常变化，作为 A 股 AI/GPU 概念板块的先行信号。**

底层逻辑：
- 当 AI 软件生态加速成熟（PR 合并加速、Issue 响应变快），说明技术突破在发生
- 当 GPU 算力供不应求（现货价格上涨、政采金额攀升），说明需求端在扩张
- 以上两者共振时，相关上市公司的基本面改善预期会被强化，股价大概率跟随

这本质上是一种**领先指标（Leading Indicator）策略**——试图在市场共识形成之前，通过产业链底层数据捕捉信号。

---

## 2. 重新设计

### 2.1 系统定位

在现有架构中新增一个**另类数据源服务**和对应的**策略模块**，而不是独立建系统。

```
现有架构适配：
┌─────────────────────────────────────────────────────┐
│ 策略层 (quant-strategy)                              │
│   └─ strategies/alt_data/  ← 新增 AI 生态策略模块    │
├─────────────────────────────────────────────────────┤
│ 处理层 (get-stockdata)                               │
│   └─ 新增另类数据的存储/查询接口                      │
├─────────────────────────────────────────────────────┤
│ 源数据层                                             │
│   ├─ mootdx-source (已有：行情)                      │
│   └─ altdata-source ← 新增：另类数据采集服务          │
└─────────────────────────────────────────────────────┘
```

### 2.2 数据源设计

只选取**确定可获取**的数据源，按可行性分级：

#### Tier 1：GitHub API（确定可行）

| 项目 | 说明 |
|---|---|
| **数据源** | GitHub REST API v3 (使用 Personal Access Token) |
| **速率限制** | 5000 次/小时/Token，**严格遵守，不绕过** |
| **采集频率** | 每 6 小时一次（每日 4 轮） |
| **目标仓库** | 配置化，初始清单见下方 |
| **采集指标** | 见下方指标定义 |

**初始目标仓库清单**（YAML 配置化，可随时增减）：

```yaml
repositories:
  # 国产 AI 框架
  - org: PaddlePaddle
    repos: [Paddle, PaddleNLP, PaddleOCR]
    label: paddle
  - org: mindspore-ai
    repos: [mindspore]
    label: mindspore
  # 大模型算子
  - org: deepseek-ai
    repos: [DeepSeek-V3, DeepSeek-Coder-V2]
    label: deepseek
  # 推理框架
  - org: vllm-project
    repos: [vllm]
    label: vllm
  - org: sgl-project
    repos: [sglang]
    label: sglang
```

**采集指标定义（每仓库）：**

| 指标 | 计算方式 | 存储字段 |
|---|---|---|
| `pr_merged_count` | 过去 7 天 merged PR 数量 | INT |
| `pr_merged_acceleration` | 本周 merged PR 数 - 上周 merged PR 数 | INT |
| `issue_close_median_hours` | 过去 30 天 closed issue 的中位响应时间（小时） | FLOAT |
| `star_delta_7d` | 过去 7 天新增 star 数 | INT |
| `commit_count_7d` | 过去 7 天 commit 数（默认分支） | INT |
| `contributor_count_30d` | 过去 30 天活跃贡献者数 | INT |

#### Tier 2：Gitee API（确定可行，优先级略低）

与 GitHub 相同的指标，用于覆盖纯国内项目（如昇腾 CANN 等仅在 Gitee 发布的项目）。

#### Tier 3：政府采购数据（需验证）

> [!WARNING]
> 此数据源依赖网页爬取 + NLP 抽取，工程复杂度高、数据质量不稳定。
> **建议：先完成 Tier 1 的闭环验证后，再决定是否投入。**

- 目标：中国政府采购网中标公告
- 关键词过滤：`GPU`、`算力`、`人工智能`、`训推一体`、`智算中心`
- 抽取字段：`(中标供应商, 品牌/型号, 金额, 日期, 采购单位)`
- 频率：每日一次

#### ~~Tier X：云算力现货价格~~（暂不纳入）

各云厂商无公开的实时库存/定价 API，此数据源不可行。如未来有厂商开放相关 API，再考虑接入。

---

### 2.3 存储设计

复用现有 ClickHouse，新建两张表：

```sql
-- 1. 仓库级别原始指标（每次采集写入一行）
CREATE TABLE altdata.github_repo_metrics
(
    `collect_time` DateTime,           -- 采集时间
    `org` String,                      -- 组织名
    `repo` String,                     -- 仓库名
    `label` String,                    -- 分组标签 (paddle/deepseek/...)
    `pr_merged_count` UInt32,          -- 7日 merged PR 数
    `pr_merged_acceleration` Int32,    -- PR 加速度
    `issue_close_median_hours` Float64,-- Issue 中位响应时间
    `star_delta_7d` Int32,             -- 7日新增 star
    `commit_count_7d` UInt32,          -- 7日 commit 数
    `contributor_count_30d` UInt32     -- 30日活跃贡献者
)
ENGINE = MergeTree()
ORDER BY (label, org, repo, collect_time)
TTL collect_time + INTERVAL 1 YEAR;

-- 2. 标签级聚合信号（由策略引擎写入）
CREATE TABLE altdata.ecosystem_signals
(
    `signal_time` DateTime,
    `label` String,                    -- 生态标签
    `composite_z_score` Float64,       -- 综合 Z-score
    `dominant_factor` String,          -- 主导因子名称
    `signal_level` Enum8('NEUTRAL'=0, 'WARM'=1, 'HOT'=2, 'EXTREME'=3),
    `detail` String                    -- JSON 格式详情
)
ENGINE = MergeTree()
ORDER BY (label, signal_time);
```

---

### 2.4 策略逻辑设计

#### 2.4.1 特征工程

对每个 `label`（如 `deepseek`），将其下所有仓库的原始指标聚合后，计算以下复合特征：

| 复合特征 | 计算方式 |
|---|---|
| `eco_momentum` | 所有仓库 `pr_merged_acceleration` 的加权和（按仓库 star 数加权） |
| `eco_responsiveness` | `issue_close_median_hours` 的倒数（越小越好 → 取倒数后越大越好） |
| `eco_growth` | `star_delta_7d` + `contributor_count_30d` 的标准化加权 |

#### 2.4.2 信号生成

```
输入：过去 90 天的 eco_momentum / eco_responsiveness / eco_growth 时序
           ↓
      滚动窗口 (30天) 计算 μ 和 σ
           ↓
      当前值的 Z-score = (x - μ) / σ
           ↓
      综合 Z-score = w1*Z(momentum) + w2*Z(responsiveness) + w3*Z(growth)
      （权重可配置，默认 0.5 / 0.2 / 0.3）
           ↓
     ┌─────────────────────────────────────────┐
     │ Z < 1.0          → NEUTRAL (无信号)     │
     │ 1.0 ≤ Z < 1.5    → WARM (关注)          │
     │ 1.5 ≤ Z < 2.0    → HOT (强信号)         │
     │ Z ≥ 2.0          → EXTREME (极端信号)    │
     └─────────────────────────────────────────┘
```

#### 2.4.3 与行情数据交叉验证

信号不直接用于交易。它作为**辅助维度**注入现有策略框架：

```
生态信号 (WARM/HOT/EXTREME)
         ↓
 关联到 A 股概念板块（如：昇腾概念 → 海光信息/寒武纪/中科曙光 等）
         ↓
 在现有股票池筛选中，对命中的股票加权：
   - WARM:    候选池评分 +5%
   - HOT:     候选池评分 +10%
   - EXTREME: 候选池评分 +15% 并触发人工关注通知
```

这种设计的好处：
1. **不独立决策**——另类数据只是增强信号，不会单独触发买卖
2. **可回测**——可以用历史 GitHub 数据回测信号与股价的相关性
3. **可降级**——另类数据源故障时，现有策略完全不受影响

---

### 2.5 服务架构

#### `altdata-source` 服务（新增）

```
services/altdata-source/
├── src/
│   ├── main.py              # FastAPI 入口
│   ├── collectors/
│   │   ├── github.py         # GitHub API 采集器
│   │   ├── gitee.py          # Gitee API 采集器
│   │   └── base.py           # 采集器基类
│   ├── config/
│   │   └── repositories.yaml # 目标仓库配置
│   ├── models/
│   │   └── metrics.py        # 数据模型
│   └── storage/
│       └── clickhouse.py     # ClickHouse 写入
├── Dockerfile
└── requirements.txt
```

**关键设计约束：**
- 使用 `asyncio` + `httpx` 做异步 HTTP 请求
- Token 轮换：配置多个 GitHub Token，按请求轮流使用
- 严格遵守 Rate Limit：读取响应头 `X-RateLimit-Remaining`，到阈值自动暂停
- 采集失败的仓库记录日志，不阻塞其他仓库

#### `quant-strategy` 集成（修改）

```
services/quant-strategy/src/
├── strategies/
│   └── alt_data/
│       ├── __init__.py
│       ├── eco_signal_strategy.py  # 信号计算逻辑
│       └── config.yaml             # 权重、阈值等参数
├── dao/
│   └── altdata_dao.py              # 读取 altdata 表
```

---

### 2.6 调度与运维

| 任务 | 频率 | 执行方式 |
|---|---|---|
| GitHub 数据采集 | 每 6 小时 | `task-orchestrator` 下发指令到 `altdata-source` |
| 生态信号计算 | 每日 20:00（盘后） | `quant-strategy` 定时任务 |
| 信号注入股票池 | 每日选股流程中自动读取 | 现有 `CandidatePoolService` 插件化集成 |

---

## 3. 开发建议

### 3.1 分阶段交付

| 阶段 | 内容 | 预计工期 | 交付标准 |
|---|---|---|---|
| **PoC** | 仅 GitHub 采集 + 本地计算 Z-score + 输出 CSV | 2-3 天 | 能看到 30 天趋势 |
| **MVP** | `altdata-source` 服务化 + ClickHouse 存储 + 手动查看信号 | 3-4 天 | 自动采集、持久化、可查询 |
| **集成** | 信号注入 `quant-strategy` 选股流程 | 2-3 天 | 选股报告中出现生态评分 |
| **回测** | 用历史 GitHub 数据回测信号与股价关联 | 3-5 天 | 得到统计结论 |

### 3.2 关键风险

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| GitHub Token 被封 | 数据断层 | 多 Token 轮换 + 严守 Rate Limit |
| 仓库被删/重命名 | 时序中断 | 采集前检查仓库状态，异常告警 |
| 信号与股价无统计相关性 | 策略无效 | PoC 阶段先做简单回测，不通过则止损 |
| 概念板块映射不准 | 信号错配 | 手动维护概念→股票映射表，定期审核 |

---

## 4. 待确认事项（已确认）

| # | 事项 | 结论 | 依据 |
|---|---|---|---|
| 1 | 是否启动开发 | **是** | EPIC-001~005 已全部完成，开发路线图已通关闭环，有空间启动新 EPIC |
| 2 | GitHub Token | **需用户提供 3-5 个 PAT** | 现有项目无 GitHub Token 配置先例，需新增环境变量 `GITHUB_TOKENS`（逗号分隔） |
| 3 | 仓库清单 | **使用设计文档中的初始清单** | 配置化设计（YAML），后续可随时增减，无需一开始就完美 |
| 4 | 概念→股票映射 | **复用现有 `IndustryDAO.get_stock_concepts()` 通道** | 系统已具备同花顺概念板块的正向/反向查询，通过 gRPC → `mootdx-source` ClickHouse handler 实现。只需维护一张 `label → 概念板块名` 的映射配置 |

### 概念映射配置示例

```yaml
# label → 对应的同花顺概念板块名（通过现有 PeerSelector 通道查询成分股）
label_concept_mapping:
  paddle: ["百度概念", "人工智能"]
  mindspore: ["华为概念", "人工智能"]
  deepseek: ["人工智能", "算力概念"]
  vllm: ["人工智能", "算力概念"]
  sglang: ["人工智能", "算力概念"]
```

通过此映射，当某个 `label` 的生态信号触发时，系统调用 `IndustryDAO.get_stock_concepts()` 反向查询概念板块成分股，即可获得受影响的 A 股标的列表。
