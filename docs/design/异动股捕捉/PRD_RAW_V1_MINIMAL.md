# L8 异动池 v1 极简版 PRD:A 视图(决策支持)+ D 视图最简延伸

## 背景

### 当前状态

`ads_l8_unified_signal` 已实施,采用单一 `anomaly_score` 加权评分,Top 10 推送。已知问题:

- 评分分布偏态,Top 50 集中在 90+,跨板块归一未做
- 权重 `0.3·pct_chg + 0.3·volume + 0.2·event + 0.2·position` 拍脑袋,无回测依据
- 评分系统**没有评估能力** —— 不知道当前胜率多少,也无从判断改动是否改善
- 评分系统在**极端市况**(普涨/普跌)下完全失效,但当前无应对

### 设计哲学(讨论锁定)

- 评估系统先于评分系统建立(回测 = 淘汰工具,不是预测工具)
- 鲁棒性 > 拟合度,简单可解释 > 复杂高拟合
- 接受策略半衰期,不追求"一次设计永久有效"
- L8 服务 4 种潜在目的(决策 / 训练 / 验证 / 温度计),近期聚焦 A 决策,长远全要,行情阶段切换主导

### 为什么是"极简 + 留扩展位"

完整版(评估 + 评分改造 + 监控 + A/B + 4 视图)对个人项目过度工程。极简版做"骨架 + 关键扩展槽":

- **数据层一次到位**(字段、单位、命名规范)
- **应用层只点亮 A 视图**(单一目的,工程量可控)
- **D 视图最简延伸**作为极端市况兜底
- **B / C 视图、F3 升级、A/B 实验、特征卡片**全部留扩展位,不在第一版实现

---

## 目标

### 业务目标

- 建立 L8 评估能力:每月一份分组诊断报告,知道当前评分公式真实胜率
- 极端市况下系统不失语:普涨/普跌日切换到 D 视图最简版(板块强弱 + 连板梯队)
- 第一版工程量控制在 **10-12 个工作日**

### 技术目标

- `ads_l8_unified_signal` 增量加 4 字段,不动现有字段语义
- 新增 2 张表(`ads_l8_backtest_label` / `ads_l8_backtest_result`)
- 新增 4 个脚本(评分时打分类标签 / T+N 回填 / 月度回测 / 月度报告)
- 不引入新基础设施,沿用 MySQL 5.7 + ClickHouse 双写 + 现有调度框架

---

## 范围

### 包含

- 主表 `ads_l8_unified_signal` schema 改造(+4 字段)
- 异动分类(F1 阶段,4 类单标签粗分类:C1/C2/C3/C4)
- 评估子系统(标注表 + 历史回填 + 月度回测 + 月度报告)
- 极端市况门控(普涨/普跌切换推送策略)
- D 视图最简延伸(市况切换时的兜底产出)
- 异动管线 v1.1 部署方案的 E5 增补 task
- 项目文档同步更新

### 不包含(延伸到后续版本)

- A/B 实验机制(留 source_version 字段,不实施实验)
- 在线衰退监控告警(月度报告人工 review 即可)
- 特征卡片登记(评分公式简单,不需要审核流程)
- 板块归一化(component_score JSON 留扩展位,但本版不实现)
- 4 类多标签 + 主类优先级(F1 阶段单标签命中即停)
- 推送场景过滤层(F1 阶段全市场推送)
- 分笔数据接入(前置条件未达成)
- B 视图(认知训练样本)、C 视图(假设验证池)
- 跨网架构改造(沿用现有云端/内网双写)

---

## 非目标(明确不做)

| 不做的事 | 为什么不做 | 留位方式 |
|---|---|---|
| 不替换现有 6 类 `signal_type` | signal_type 是现象层分类,与机制层 anomaly_category 共存 | 主表两个字段并存 |
| 不修改现有评分公式 0.3/0.3/0.2/0.2 | 评估系统建成前没有改动依据 | dim_anomaly_score_weight 加 v1 一行,固化当前公式 |
| 不做实时盘中异动 | L8 是盘后系统,定位明确 | - |
| 不做用户偏好的个性化推送 | 个人项目无此需求 | - |
| 不做异动股自动跟踪和持仓建议 | 项目定位是"观察 + 训练",不是交易系统 | - |
| 不做高级评分模型(XGBoost / NN) | 黑盒模型在 A 股环境下半衰期短,违背可解释性原则 | - |

---

## E1 主表 `ads_l8_unified_signal` 增量改造

**Epic 描述**:在不动现有字段的前提下,加 4 个字段为后续评估、扩展、视图切换打基础。预计耗时 2 个工作日。

### E1-S1 主表加 4 字段

**作为** L8 评分流程,**我希望** 主表能记录评分版本、异动机制分类、评分溯源和推送状态,**以便** 评估系统能按版本回测、按分类分组、按推送状态过滤。

#### 任务

- E1-S1-T1 编写 `ALTER TABLE` 迁移脚本(MySQL)
- E1-S1-T2 编写 ClickHouse 同步表的对应字段添加脚本
- E1-S1-T3 跨仓 schema 变更四件套(变更说明 / 影响清单 / 迁移脚本 / rollback)
- E1-S1-T4 在 `IMPLEMENTATION_FEEDBACK.md` 标注跨仓变更

#### 字段定义

| 字段 | 类型 | 默认值 | 含义 |
|---|---|---|---|
| `source_version` | VARCHAR(16) NOT NULL DEFAULT 'v1' | 'v1' | 评分公式版本号,留 A/B 实验扩展位 |
| `anomaly_category` | VARCHAR(8) NULL | NULL | 4 类机制分类(C1/C2/C3/C4),F1 阶段单标签 |
| `component_score` | JSON NULL | NULL | 评分溯源,各分量贡献拆解 |
| `is_pushed` | TINYINT(1) NOT NULL DEFAULT 1 | 1 | 是否推送给用户(极端市况门控置 0) |

#### DDL 示例

```sql
-- MySQL 5.7
ALTER TABLE `ads_l8_unified_signal`
  ADD COLUMN `source_version` VARCHAR(16) NOT NULL DEFAULT 'v1' COMMENT '评分公式版本号',
  ADD COLUMN `anomaly_category` VARCHAR(8) DEFAULT NULL COMMENT 'F3 机制分类:C1/C2/C3/C4',
  ADD COLUMN `component_score` JSON DEFAULT NULL COMMENT '评分分量溯源 JSON',
  ADD COLUMN `is_pushed` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否推送(极端市况置 0)',
  ADD KEY `idx_category_pushed` (`trade_date`, `anomaly_category`, `is_pushed`);

-- 历史数据初始化
UPDATE `ads_l8_unified_signal`
SET `source_version` = 'v1',
    `is_pushed` = 1
WHERE `source_version` IS NULL OR `source_version` = '';
```

#### 验收标准

- **AC1**:字段添加完成且无业务中断
  - **Given** 主表已存在百万级历史数据
  - **When** 执行 `ALTER TABLE` 迁移脚本
  - **Then** 所有历史行的 `source_version='v1'`、`is_pushed=1`,新写入逻辑能写入 `anomaly_category` 和 `component_score`

- **AC2**:索引可用
  - **Given** 加完 `idx_category_pushed` 索引
  - **When** 执行 `EXPLAIN SELECT * FROM ads_l8_unified_signal WHERE trade_date = ? AND anomaly_category = 'C2' AND is_pushed = 1`
  - **Then** `key` 列显示命中 `idx_category_pushed`

- **AC3**:双写一致
  - **Given** MySQL 改造完成
  - **When** ClickHouse 同步表执行对应 ADD COLUMN
  - **Then** 双写脚本能正常写入两边,且字段一致性校验通过

### E1-S2 激活 `dim_anomaly_score_weight` 版本化使用

**作为** 评分公式管理者,**我希望** 把当前评分公式固化为 v1,**以便** 未来评分公式调整时能与 v1 对照回测。

#### 任务

- E1-S2-T1 在 `dim_anomaly_score_weight` 写入 v1 配置(4 个权重 + meta)
- E1-S2-T2 评分代码读取 v1 权重配置,而不是硬编码

#### 配置示例

```sql
INSERT INTO `dim_anomaly_score_weight` 
  (`version`, `weight_key`, `weight_value`, `is_active`, `created_at`)
VALUES
  ('v1', 'score_pct_chg', 0.3, 1, NOW()),
  ('v1', 'score_volume',  0.3, 1, NOW()),
  ('v1', 'score_event',   0.2, 1, NOW()),
  ('v1', 'score_position',0.2, 1, NOW());
```

#### 验收标准

- **AC1**:评分代码读配置不读硬编码
  - **Given** v1 配置已写入
  - **When** 17:30 评分流程启动
  - **Then** 日志中出现 `[anomaly_score] using version=v1, weights={pct_chg: 0.3, volume: 0.3, event: 0.2, position: 0.2}`

---

## E2 评估子系统(P0,核心)

**Epic 描述**:建立 L8 的回测能力。新增 2 张表,4 个脚本。预计耗时 5-6 个工作日。

### E2-S1 标注表 `ads_l8_backtest_label` 建表

**作为** 评估系统,**我希望** 有一张专门记录每条推送的事后表现的表,**以便** 月度回测能基于历史标注做胜率统计。

#### 任务

- E2-S1-T1 编写建表 DDL(MySQL + ClickHouse 双写)
- E2-S1-T2 在 `TABLES_INDEX.md` 增加表元数据
- E2-S1-T3 主键 + 索引设计

#### DDL

```sql
CREATE TABLE `ads_l8_backtest_label` (
  `ts_code`           VARCHAR(20) NOT NULL COMMENT '完整代码,如 600519.SH',
  `trade_date`        DATE        NOT NULL COMMENT '推送当日交易日',
  `source_version`    VARCHAR(16) NOT NULL DEFAULT 'v1' COMMENT '评分公式版本',
  `anomaly_category`  VARCHAR(8)  DEFAULT NULL COMMENT 'F3 机制分类',
  `raw_score`         DECIMAL(10,4) DEFAULT NULL COMMENT '推送当日 anomaly_score',
  `is_pushed`         TINYINT(1)  NOT NULL DEFAULT 1 COMMENT '是否进入 Top N 推送',
  
  -- 事后实际表现(T+N 回填)
  `ret_t1`            DECIMAL(10,6) DEFAULT NULL COMMENT 'T+1 涨跌幅(小数)',
  `ret_t5`            DECIMAL(10,6) DEFAULT NULL COMMENT 'T+5 累计涨跌幅(小数)',
  `ret_t10`           DECIMAL(10,6) DEFAULT NULL COMMENT 'T+10 累计涨跌幅(小数)',
  `ret_t30`           DECIMAL(10,6) DEFAULT NULL COMMENT 'T+30 累计涨跌幅(小数)',
  
  -- 基准与超额
  `benchmark_ret_t5`  DECIMAL(10,6) DEFAULT NULL COMMENT '同期沪深300涨跌幅(小数)',
  `sector_ret_t5`     DECIMAL(10,6) DEFAULT NULL COMMENT '同期所属申万 l1 行业涨跌幅(小数)',
  `alpha_t5`          DECIMAL(10,6) DEFAULT NULL COMMENT 'ret_t5 - benchmark_ret_t5(小数)',
  `hit_t5`            TINYINT(1)    DEFAULT NULL COMMENT 'alpha_t5 > 0 ? 1 : 0',
  
  -- 上下文
  `market_regime`     VARCHAR(16)   DEFAULT NULL COMMENT '推送日市场状态:broad_up/broad_down/structural/low_vol',
  `industry_l1`       VARCHAR(32)   DEFAULT NULL COMMENT '所属申万 l1 行业',
  `board`             VARCHAR(8)    DEFAULT NULL COMMENT '板块:main/gem/star/bj',
  
  -- 标准尾部三件套
  `created_at`  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at`  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_deleted`  TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除',
  
  PRIMARY KEY (`ts_code`, `trade_date`, `source_version`),
  KEY `idx_trade_date` (`trade_date`),
  KEY `idx_category_regime` (`anomaly_category`, `market_regime`),
  KEY `idx_updated_at` (`updated_at`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC
  COMMENT='L8 异动池标注表(用于评估子系统回测)';
```

#### 验收标准

- **AC1**:DDL 通过 lint 校验
  - **Given** DDL 提交
  - **When** 在 MySQL 5.7 测试环境执行
  - **Then** 建表成功,字段类型 / 默认值 / 索引全部符合规范

- **AC2**:跨仓 schema 文档同步
  - **Given** 表创建完成
  - **When** 检查 `TABLES_INDEX.md` 和 `IMPLEMENTATION_FEEDBACK.md`
  - **Then** 两份文档都已更新对应条目

### E2-S2 历史数据回填脚本

**作为** 评估系统,**我希望** 把过去 N 个交易日的推送数据回填到标注表,**以便** 月度回测有足够样本量(目标:覆盖近 1 年 ≥ 200 个交易日)。

#### 任务

- E2-S2-T1 编写历史回填脚本(Python),从 `ads_l8_unified_signal` 读历史推送 → 写入 `ads_l8_backtest_label`
- E2-S2-T2 关联 `stock_kline_daily` 计算 T+1/5/10/30 实际涨跌
- E2-S2-T3 关联 `ods_index_daily`(沪深 300)计算基准
- E2-S2-T4 关联 `ads_l1_market_overview` 标记 market_regime
- E2-S2-T5 跨长假涨跌幅计算用 `meta_trading_calendar.next_trade_date` 链路,**不能用日历日加减**

#### 关键 SQL 片段

```sql
-- 获取 T+5 实际涨跌幅(基于交易日历,不是自然日)
-- 假设传入 base_date = '2025-04-01'
SELECT k.ts_code,
       k.close AS close_t5,
       (k.close / base.close - 1) AS ret_t5  -- 单位:小数
FROM `stock_kline_daily` k
JOIN `stock_kline_daily` base 
  ON k.ts_code = base.ts_code AND base.trade_date = '2025-04-01'
WHERE k.trade_date = (
    -- 取 base_date 后第 5 个 is_open=1 的日期
    SELECT cal_date FROM (
      SELECT cal_date FROM `meta_trading_calendar`
      WHERE cal_date > '2025-04-01' AND is_open = 1
      ORDER BY cal_date ASC LIMIT 5
    ) t ORDER BY cal_date DESC LIMIT 1
  )
  AND k.is_deleted = 0
  AND base.is_deleted = 0;
```

#### 验收标准

- **AC1**:历史回填覆盖率
  - **Given** 已有 250+ 个交易日的 ads_l8_unified_signal 历史数据
  - **When** 执行历史回填脚本(批处理跑在 ClickHouse 上)
  - **Then** `ads_l8_backtest_label` 中,past 200 个交易日的标注样本中,`ret_t5` 字段非空率 ≥ 95%

- **AC2**:跨长假计算正确
  - **Given** base_date = 2025-09-26(国庆前最后一个交易日)
  - **When** 计算 ret_t5
  - **Then** 选取的 T+5 日期是 2025-10-15(节后第 5 个交易日,跳过国庆假期),不是 2025-10-01

- **AC3**:基准与板块字段填充
  - **Given** 一条标注记录的 ts_code = '600519.SH'(申万 l1: 食品饮料)
  - **When** 检查该记录
  - **Then** `industry_l1 = '食品饮料'`,`board = 'main'`,`benchmark_ret_t5` 非空,`sector_ret_t5` 非空

### E2-S3 每日 T+N 增量回填脚本

**作为** 评估系统,**我希望** 每日凌晨自动回填 T+1/T+5/T+10/T+30 的实际涨跌数据,**以便** 标注表持续更新。

#### 任务

- E2-S3-T1 编写每日回填脚本(增量逻辑)
- E2-S3-T2 接入 `meta_pipeline_run` 调度
- E2-S3-T3 失败重试机制(单日失败次日补)

#### 调度时点

```
每个交易日 09:00:
  - 回填 T+1: 把 (today - 1 trade_day) 的推送的 ret_t1 填上
  - 回填 T+5: 把 (today - 5 trade_days) 的推送的 ret_t5 填上
  - 回填 T+10: 把 (today - 10 trade_days) 的推送的 ret_t10 填上
  - 回填 T+30: 把 (today - 30 trade_days) 的推送的 ret_t30 填上
```

#### 验收标准

- **AC1**:每日回填准时
  - **Given** 当前是交易日 T,前一交易日 T-1 已有 Top 10 推送
  - **When** 当日 09:00 触发回填脚本
  - **Then** T-1 那批推送在 09:30 前完成 ret_t1 字段填充

- **AC2**:失败可重试
  - **Given** 某日因数据延迟回填失败
  - **When** 次日 09:00 重新触发
  - **Then** 之前失败的标注样本被一并补全,不出现永久缺数据

### E2-S4 月度回测脚本

**作为** 系统维护者,**我希望** 每月跑一次回测,产出按 4 类异动 + 市场状态 + 板块的分组诊断,**以便** 知道当前评分公式真实胜率,以及假异动主要分布在哪。

#### 任务

- E2-S4-T1 编写月度回测脚本(Python + ClickHouse)
- E2-S4-T2 实现 6 个 baseline 对照(B0-B5)
- E2-S4-T3 分组聚合(按 anomaly_category × market_regime × board × score_bin)
- E2-S4-T4 输出 `ads_l8_backtest_result` 表

#### 关键 baseline

| Baseline ID | 规则 |
|---|---|
| B0 | 当日全 A 随机抽 10 只(剔除 ST、上市 < 60 个交易日、停牌、B 股) |
| B1 | 沪深 300 ETF 等权(`510300.SH`) |
| B2 | 当日涨幅 Top 10(剔除条件同 B0) |
| B3 | 当日量比 Top 10 |
| B4 | 当日 LHB 上榜池随机 10 只 |
| B5 | 当前 L8 v1 公式 Top 10(本系统现状) |

#### 结果表 DDL

```sql
CREATE TABLE `ads_l8_backtest_result` (
  `run_id`            VARCHAR(32) NOT NULL COMMENT '回测运行 ID(留扩展位)',
  `run_date`          DATE        NOT NULL COMMENT '回测执行日',
  `period_start`      DATE        NOT NULL COMMENT '回测样本起始日',
  `period_end`        DATE        NOT NULL COMMENT '回测样本结束日',
  `source_version`    VARCHAR(16) NOT NULL DEFAULT 'v1' COMMENT '评分版本',
  `baseline_id`       VARCHAR(8)  DEFAULT NULL COMMENT 'B0-B5 标识,NULL 表示主结果',
  
  -- 分组维度
  `anomaly_category`  VARCHAR(8)  DEFAULT NULL COMMENT 'C1/C2/C3/C4 或 ALL',
  `market_regime`     VARCHAR(16) DEFAULT NULL COMMENT '市场状态或 ALL',
  `board`             VARCHAR(8)  DEFAULT NULL COMMENT '板块或 ALL',
  `score_bin`         VARCHAR(16) DEFAULT NULL COMMENT '评分区间或 ALL,如 90+/80-90/70-80',
  
  -- 度量指标
  `sample_size`       INT          NOT NULL COMMENT '样本量',
  `hit_rate_t5`       DECIMAL(8,6) DEFAULT NULL COMMENT 'T+5 胜率(alpha > 0 比例)',
  `mean_alpha_t5`     DECIMAL(10,6) DEFAULT NULL COMMENT 'T+5 平均超额收益(小数)',
  `median_alpha_t5`   DECIMAL(10,6) DEFAULT NULL COMMENT 'T+5 中位数超额收益(小数)',
  `mean_ret_t5`       DECIMAL(10,6) DEFAULT NULL COMMENT 'T+5 平均绝对涨跌幅(小数)',
  
  `created_at`  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`  TINYINT(1) NOT NULL DEFAULT 0,
  
  PRIMARY KEY (`run_id`, `source_version`, `anomaly_category`, `market_regime`, `board`, `score_bin`),
  KEY `idx_run_date` (`run_date`),
  KEY `idx_baseline` (`baseline_id`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC
  COMMENT='L8 月度回测结果汇总';
```

#### 验收标准

- **AC1**:月度回测产出完整
  - **Given** 标注表有近 90 个交易日数据
  - **When** 执行月度回测脚本
  - **Then** `ads_l8_backtest_result` 中包含:
    - 主结果:4 类 × 4 状态 × 4 板块 × 3 评分区间 = 192 行(含 ALL 维度的聚合)
    - Baseline 结果:B0-B5 各产出 1 行(period_end 维度的整体)

- **AC2**:统计显著性可见
  - **Given** 回测结果产出
  - **When** 检查 `sample_size` 字段
  - **Then** 任何 sample_size < 30 的分组,后续报告中标注"样本不足,结论参考价值低"

### E2-S5 月度报告 markdown 生成

**作为** 系统维护者,**我希望** 月度回测后自动生成可读报告,**以便** 我每月只看一次就能掌握 L8 真实表现。

#### 任务

- E2-S5-T1 编写报告模板(Jinja2 / 直接 f-string)
- E2-S5-T2 从 `ads_l8_backtest_result` 拉取数据填充
- E2-S5-T3 输出到 `reports/l8_backtest_{YYYYMM}.md`

#### 报告结构

```markdown
# L8 异动池 v1 月度回测报告 - 2026-05

## 总体表现
- 推送总数:N
- T+5 胜率:X.XX%(对比沪深300基准)
- T+5 平均超额收益:X.XX%
- vs Baseline:
  - vs B0 随机:+X pp
  - vs B2 涨幅 Top 10:+X pp
  - **关键观察**:如果 vs B2 < +3pp,说明现有评分公式相对单一规则没有显著优势

## 分类诊断(F3 4 类)
| 类别 | 样本量 | 胜率 | 平均超额 | 备注 |
|---|---|---|---|---|
| C1 短线封板 | ... | ... | ... | ... |
| C2 中线连板/题材 | ... | ... | ... | ... |
| C3 资金驱动 | ... | ... | ... | ... |
| C4 事件驱动 | ... | ... | ... | ... |

## 市场状态诊断
...

## 板块诊断
...

## 评分区间诊断
- Top 50(score 90+)真实胜率
- 80-90 区间胜率
- 70-80 区间胜率

## 关键发现
- (脚本自动生成 3-5 条最显著的发现,如"C4 事件驱动在 broad_down 状态下胜率仅 35%,显著低于其他状态")

## 建议
- 自动生成基于阈值的建议,如"建议下个版本考虑 [...]"
```

#### 验收标准

- **AC1**:报告按时产出
  - **Given** 每月 1 号凌晨 02:00 月度回测完成
  - **When** 报告生成脚本触发
  - **Then** `reports/l8_backtest_{YYYYMM}.md` 文件在 03:00 前生成

- **AC2**:报告可读性
  - **Given** 报告生成完成
  - **When** 用户在 5 分钟内浏览
  - **Then** 能立刻看出当前 L8 vs 各 Baseline 的相对表现,以及哪类异动是噪音重灾区

---

## E3 异动分类逻辑(F1 阶段单标签)

**Epic 描述**:实现 4 类异动的单标签判定逻辑,在 17:30 评分时打标。预计耗时 1-2 个工作日。

### E3-S1 4 类(C1-C4)单标签判定函数

**作为** 17:30 评分流程,**我希望** 给每只异动股打一个 anomaly_category 标签,**以便** 评估系统能按机制分组诊断。

#### 任务

- E3-S1-T1 实现分类函数(Python)
- E3-S1-T2 在 17:30 评分流程中插入分类逻辑
- E3-S1-T3 写入主表 `anomaly_category` 字段

#### 分类逻辑(顺序判定,命中即停)

```python
def classify_anomaly(stock_signals: dict) -> str:
    """
    F1 阶段单标签分类。命中即停,永不重叠。
    
    输入: stock_signals 包含以下字段:
      - has_event_today: bool (来自 ads_l8_unified_signal.has_event_today)
      - board_height: int (来自 ods_event_limit_pool.board_height,无则 0)
      - has_lhb: bool (当日是否在龙虎榜)
      - has_north_anomaly: bool (北向资金净买异常,阈值 TBD)
    
    输出: 'C1' / 'C2' / 'C3' / 'C4'
    """
    # 优先级 1: 事件驱动
    if stock_signals.get('has_event_today'):
        return 'C4'
    
    # 优先级 2: 中线连板/题材
    if stock_signals.get('board_height', 0) >= 3:
        return 'C2'
    
    # 优先级 3: 资金驱动
    if stock_signals.get('has_lhb') or stock_signals.get('has_north_anomaly'):
        return 'C3'
    
    # 优先级 4: 短线封板/普通异动
    return 'C1'
```

#### 类别定义文档(写入 `dim_*` 字典或代码注释)

| 类别 | 名称 | 定义 | 主要机制 |
|---|---|---|---|
| C1 | 短线封板/普通异动 | board_height ≤ 2 且无事件无 LHB 无北向异常 | 资金锁仓 + 卖压消失 |
| C2 | 中线连板/题材 | board_height ≥ 3,且无事件 | 情绪溢价 + 赚钱效应 |
| C3 | 资金驱动 | LHB 上榜 或 北向资金异常 | 主力资金行为 |
| C4 | 事件驱动 | 当日有事件(增减持/回购/分红/ST/调查/业绩) | 信息事件冲击 |

#### 验收标准

- **AC1**:分类覆盖完整
  - **Given** 17:30 异动池有 100+ 只股
  - **When** 分类函数运行
  - **Then** 100% 的股都被分到 C1/C2/C3/C4 之一,没有 NULL 或异常值

- **AC2**:边界判定正确
  - **Given** 一只股 board_height = 3 且当日无事件
  - **When** 判定分类
  - **Then** anomaly_category = 'C2'(不是 C1,3 板归 C2)

- **AC3**:重叠时按优先级
  - **Given** 一只股 5 连板(命中 C2)+ LHB 上榜(命中 C3)+ 当日有重大回购(命中 C4)
  - **When** 判定分类
  - **Then** anomaly_category = 'C4'(C4 优先级高于 C2 和 C3)

### E3-S2 评分溯源 component_score 写入

**作为** 评估系统,**我希望** 每条推送都记录评分各分量的具体值,**以便** 调优时能溯源到"具体哪个特征贡献了多少分"。

#### 任务

- E3-S2-T1 在评分计算时同步生成 component_score JSON
- E3-S2-T2 写入主表 `component_score` 字段

#### JSON 结构

```json
{
  "score_pct_chg": 92.5,
  "score_volume": 88.3,
  "score_event": 50.0,
  "score_position": 75.0,
  "weighted_total": 81.4,
  "version": "v1",
  "computed_at": "2026-05-07T17:30:12+08:00"
}
```

> 第一版只存 4 个分量 + 总分 + 元信息。未来扩展位:可加 `normalized_score`(板块归一化)、`tick_modifier`(分笔置信度)、`category_specific_score`(分类目标函数下的子评分)等。

#### 验收标准

- **AC1**:JSON 结构正确
  - **Given** 17:30 评分完成
  - **When** 检查任意推送行的 component_score 字段
  - **Then** 字段是合法 JSON,包含 4 个分量 + weighted_total + version + computed_at

- **AC2**:数值一致性
  - **Given** component_score JSON 中各分量
  - **When** 用 v1 权重重算 `0.3 × pct_chg + 0.3 × volume + 0.2 × event + 0.2 × position`
  - **Then** 结果等于 weighted_total(误差 < 0.01)

---

## E4 极端市况门控 + D 视图最简延伸

**Epic 描述**:在普涨/普跌日切换推送策略,改用 D 视图最简版兜底。预计耗时 2 个工作日。

### E4-S1 极端市况识别

**作为** 17:34 推送决策环节,**我希望** 识别当日是否属于极端市况,**以便** 决定是否走 D 视图。

#### 任务

- E4-S1-T1 实现市况识别函数(读 `ads_l1_market_overview` + `ods_market_breadth_daily`)
- E4-S1-T2 阈值参数化(初版硬编码,记入 `dim_*` 配置后续可调)

#### 识别逻辑

```python
def identify_extreme_market(trade_date: date) -> dict:
    """
    返回:
      {
        'is_extreme': bool,
        'regime': 'broad_up' / 'broad_down' / 'normal',
        'limit_up_count': int,
        'limit_down_count': int,
        'should_use_d_view': bool
      }
    """
    market = query_l1_overview(trade_date)
    breadth = query_market_breadth(trade_date)
    
    limit_up_count = breadth['limit_up_count']
    limit_down_count = breadth['limit_down_count']
    regime = market['market_regime']
    
    # 锁定阈值 100(2026-05-07 决议),落地后可回测调
    # 配置写入 dim_*_threshold 配置表,代码读配置不写死
    EXTREME_LIMIT_COUNT_THRESHOLD = 100
    is_broad_up = (regime == 'broad_up' and limit_up_count > EXTREME_LIMIT_COUNT_THRESHOLD)
    is_broad_down = (regime == 'broad_down' and limit_down_count > EXTREME_LIMIT_COUNT_THRESHOLD)
    
    return {
        'is_extreme': is_broad_up or is_broad_down,
        'regime': regime,
        'limit_up_count': limit_up_count,
        'limit_down_count': limit_down_count,
        'should_use_d_view': is_broad_up or is_broad_down,
    }
```

#### 验收标准

- **AC1**:阈值正确触发
  - **Given** 当日 broad_up 状态且涨停数 = 130
  - **When** 调用 identify_extreme_market
  - **Then** is_extreme = True,should_use_d_view = True

- **AC2**:阈值边界处理
  - **Given** 当日 broad_up 状态且涨停数 = 100
  - **When** 调用 identify_extreme_market
  - **Then** is_extreme = False(严格大于,等于不触发)

- **AC3**:正常市况不触发
  - **Given** 当日 structural 状态且涨停数 = 120
  - **When** 调用 identify_extreme_market
  - **Then** is_extreme = False(只有 broad_up/broad_down 才触发)

### E4-S2 推送策略切换

**作为** 17:34 推送流程,**我希望** 极端市况下不推送个股 Top 10,而是产出 D 视图,**以便** 用户在评分系统失效的日子也能看到有意义的内容。

#### 任务

- E4-S2-T1 在 17:34 推送流程加 if 分支
- E4-S2-T2 极端市况下,把 ads_l8_unified_signal 当日所有候选 is_pushed 置 0
- E4-S2-T3 调用 D 视图生成函数

#### 验收标准

- **AC1**:极端日不推个股
  - **Given** 当日触发极端市况
  - **When** 17:34 推送流程结束
  - **Then** `app_anomaly_top10_daily` 当日记录为空,且 ads_l8_unified_signal 当日所有行 is_pushed = 0

- **AC2**:正常日推送不变
  - **Given** 当日为非极端市况
  - **When** 17:34 推送流程结束
  - **Then** 沿用原 Top 10 推送逻辑,is_pushed = 1 的行有 10 条

- **AC3**:评估自动跳过
  - **Given** 标注表中存在 is_pushed = 0 的行
  - **When** 月度回测脚本运行
  - **Then** 仅统计 is_pushed = 1 的行,极端市况不污染回测结果

### E4-S3 D 视图最简版输出

**作为** 用户,**我希望** 在普涨/普跌日打开系统看到市场状态描述而不是空白,**以便** 知道"今天市场什么样,虽然不挑股了"。

#### 任务

- E4-S3-T1 设计 `app_market_brief` 表(D 视图前端面表)
- E4-S3-T2 编写 D 视图生成函数,从 L1/L2/L4 已有数据聚合
- E4-S3-T3 写入 app 表

#### 表 DDL(新增 app_ 表)

```sql
CREATE TABLE `app_market_brief` (
  `trade_date`  DATE        NOT NULL COMMENT '交易日',
  `regime`      VARCHAR(16) NOT NULL COMMENT '市场状态',
  
  -- 全景指标(聚合自 L1)
  `sh_close`           DECIMAL(10,4) DEFAULT NULL COMMENT '上证综指收盘',
  `sh_pct_chg`         DECIMAL(10,6) DEFAULT NULL COMMENT '上证综指涨跌幅(小数)',
  `total_amount_yi`    DECIMAL(20,2) DEFAULT NULL COMMENT '全市场成交额(亿元)',
  `up_count`           INT           DEFAULT NULL COMMENT '上涨家数',
  `down_count`         INT           DEFAULT NULL COMMENT '下跌家数',
  `limit_up_count`     INT           DEFAULT NULL COMMENT '涨停家数',
  `limit_down_count`   INT           DEFAULT NULL COMMENT '跌停家数',
  
  -- 板块强弱(Top 5 + Bottom 5,JSON 数组)
  `top_industries`     JSON          DEFAULT NULL COMMENT 'Top 5 申万 l1 行业',
  `bottom_industries`  JSON          DEFAULT NULL COMMENT 'Bottom 5 申万 l1 行业',
  
  -- 连板梯队(D 视图核心)
  `board_ladder`       JSON          DEFAULT NULL COMMENT '连板梯队,如 {1:50, 2:20, 3:8, 4:3, 5+:1}',
  
  -- 触发原因
  `trigger_reason`     VARCHAR(64)   DEFAULT NULL COMMENT 'broad_up_extreme / broad_down_extreme / normal',
  `display_priority`   TINYINT(1)    DEFAULT 0  COMMENT '是否优先展示给用户(1=极端日,0=常态日)',
  
  -- 标准尾部
  `created_at`  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_deleted`  TINYINT(1) NOT NULL DEFAULT 0,
  
  PRIMARY KEY (`trade_date`),
  KEY `idx_priority` (`display_priority`, `trade_date`)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC
  COMMENT='市场全景简报(D 视图,极端市况兜底展示)';
```

#### D 视图核心展示字段(前端用)

| 字段 | 数据来源 | 备注 |
|---|---|---|
| 市场状态 | ads_l1_market_overview.market_regime | 直接展示 |
| 上证涨跌 | ads_l1_market_overview.idx_sh_pct | 配色按正负 |
| 总成交额 | ads_l1_market_overview.turnover_total | 单位:亿元 |
| 涨跌家数 | ods_market_breadth_daily | 直接展示 |
| 涨跌停家数 | ods_market_breadth_daily | 极端日重点 |
| Top 5 行业 | ads_l2_industry_daily 排序 | 行业涨跌龙虎榜 |
| Bottom 5 行业 | 同上 | 弱势行业 |
| 连板梯队 | ods_event_limit_pool 聚合 | 极端日核心,反映市场情绪结构 |

#### 验收标准

- **AC1**:极端日 D 视图就绪
  - **Given** 当日触发极端市况
  - **When** 17:34 推送流程结束
  - **Then** `app_market_brief` 当日 display_priority = 1,且 board_ladder 非空

- **AC2**:常态日 D 视图也写入(but 不前置展示)
  - **Given** 当日为非极端市况
  - **When** 17:34 推送流程结束
  - **Then** `app_market_brief` 当日 display_priority = 0(数据照样写,前端不前置展示但保留扩展位)

- **AC3**:连板梯队结构正确
  - **Given** 当日有 50 只首板、20 只二板、8 只三板、3 只四板、1 只 5+ 板
  - **When** 检查 board_ladder JSON
  - **Then** `{"1": 50, "2": 20, "3": 8, "4": 3, "5+": 1}`

---

## E5 异动管线 v1.1 增补 task

**Epic 描述**:在 v1.1 部署方案的 E5 异动管线主体里加 1 个 task。预计耗时 0.5 个工作日。

### E5-S1 在 v1.1 异动管线 E5 增补打标签 task

**作为** 异动管线 v1.1 的运维者,**我希望** 在 E5 主流程里加打分类标签和写 component_score 的步骤,**以便** 主表数据完整支持评估系统。

#### 任务

- E5-S1-T1 在 v1.1 部署方案文档的 E5 章节加新 task:T1.5 评分时打分类标签 + 写 component_score
- E5-S1-T2 在 v1.1 部署方案文档的 E5 章节加新 task:T1.6 极端市况门控 + D 视图生成
- E5-S1-T3 更新 v1.1 时间线图(17:30 评分 / 17:32 极端市况判定 / 17:34 推送或 D 视图)

#### 验收标准

- **AC1**:v1.1 文档同步
  - **Given** v1.1 部署方案文档已存在
  - **When** 查看 E5 章节
  - **Then** 出现 T1.5 和 T1.6 两个新 task,描述清晰且与本 PRD 的 E3、E4 对应

---

## E6 项目文档同步更新

**Epic 描述**:更新跨章节文档,确保设计变更能被未来对话跟踪到。预计耗时 0.5 个工作日。

### E6-S1 PROJECT_OVERVIEW.md 更新

#### 任务

- E6-S1-T1 第 5 章状态加注:"v1 极简版评估子系统设计 2026-05-07 交付"
- E6-S1-T2 第 6 节决策日志加一条:`L8 评分系统:v1 极简版方向锁定,A 视图 + D 视图最简延伸 (2026-05-07)`
- E6-S1-T3 第 7 节 TBD 总账更新:
  - "L8 评分跨板块归一" → 改注 "评估子系统建成 + 60 个交易日数据后回测决定"
  - "L8 评分权重无理论依据" → 改注 "评估子系统建成 + 月度回测后调优"
  - "L8 评分分布偏态" → 改注 "评估子系统建成后用分组诊断验证是否仍是问题"

### E6-S2 TABLES_INDEX.md 更新

#### 任务

- E6-S2-T1 第 4 节 ads_* 表增加 `ads_l8_backtest_label` 行
- E6-S2-T2 第 4 节 ads_* 表增加 `ads_l8_backtest_result` 行
- E6-S2-T3 第 5 节 app_* 表增加 `app_market_brief` 行
- E6-S2-T4 修改 `ads_l8_unified_signal` 行,关键字段补充新加的 4 个

### E6-S3 IMPLEMENTATION_FEEDBACK.md 更新

#### 任务

- E6-S3-T1 第 5 章新增决策记录:"v1 极简版方向锁定 (2026-05-07)"
- E6-S3-T2 标注跨仓 schema 变更:"内网仓 → 云端仓:ads_l8_unified_signal 加 4 字段"

#### 验收标准(E6 整体)

- **AC1**:文档自洽
  - **Given** PRD 落地后
  - **When** 同步更新 3 份索引文档
  - **Then** 任一新增表 / 字段都能在 TABLES_INDEX 查到,任一决策都能在 IMPLEMENTATION_FEEDBACK 找到记录,任一 TBD 状态都能在 PROJECT_OVERVIEW 第 7 节确认

---

## 技术依赖

### 数据库

- MySQL 5.7(主写,支持事务)
- ClickHouse(双写,跑回测和大规模聚合)
- 字符集统一:utf8mb4 + utf8mb4_unicode_ci + DYNAMIC

### 上游表(已存在,不动)

| 表 | 用途 |
|---|---|
| `ads_l8_unified_signal` | 主表,改造对象 |
| `ads_l1_market_overview` | 极端市况识别(market_regime) |
| `ads_l2_industry_daily` | D 视图行业 Top/Bottom |
| `ods_event_limit_pool` | 涨跌停 + 连板梯队 |
| `ods_market_breadth_daily` | 涨跌停家数 |
| `ods_index_daily` | 沪深 300 基准 |
| `stock_kline_daily` | T+N 涨跌幅计算 |
| `meta_trading_calendar` | 跨长假交易日推算 |
| `dim_anomaly_score_weight` | 评分公式版本化(已存在,激活使用) |
| `stock_lhb_daily` | LHB 判定 |
| `stock_north_funds_daily` | 北向资金日终(2024-08-19 后口径) |

### 调度

- 复用现有 APScheduler + JSON pipeline
- 接入 `meta_pipeline_run` 任务编排
- 邮件告警复用 v1.1 框架

### 跨网

- 评估系统计算跑在内网 ClickHouse
- 月度回测结果通过双写回到云端 MySQL
- 前端 wxch-gateway 读云端 MySQL,不直连内网

---

## 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|---|---|---|---|
| 历史回填数据缺失(部分股票退市/停牌) | 中 | 中 | 标注表对缺失字段允许 NULL,回测脚本明确剔除 NULL 样本并报告剔除率 |
| ST 跨长假差分错误 | 中 | 低 | 用 `meta_trading_calendar.next_trade_date` 链路,**严禁日历日加减**(domain skill 红线) |
| 涨跌停按 9.7% 简化版导致创业板/科创板分类偏差 | 低 | 高 | 现有简化版不变,前端/报告必须注明"按主板 9.7% 简化判定" |
| 极端市况阈值 80 不准确 | 中 | 中 | 第一版硬编码,落地后用回测调优,允许 ±20 浮动 |
| 4 类分类规则在牛熊切换时不稳定 | 中 | 中 | F1 阶段单标签简化,接受边界不准确;升级到 F3 多标签时同步重测 |
| 双写一致性问题 | 高 | 低 | 沿用现有双写框架的一致性校验机制,加 schema 变更四件套 |
| 评估系统跑批占用 CK 资源 | 低 | 中 | 月度回测调度在凌晨 02:00,与生产跑批错峰 |

---

## 里程碑

| 里程碑 | 计划日期(D 表示设计冻结日) | 交付物 |
|---|---|---|
| **M1 schema 改造完成** | D+2 | ads_l8_unified_signal +4 字段 + dim_anomaly_score_weight v1 配置 + ClickHouse 同步 |
| **M2 异动分类 + 主表写入** | D+4 | E3 完成,17:30 流程能写出 anomaly_category 和 component_score |
| **M3 标注表 + 历史回填完成** | D+7 | ads_l8_backtest_label 表建成,近 200 个交易日历史回填 |
| **M4 极端市况门控 + D 视图最简版** | D+9 | E4 完成,极端日切换到 D 视图,app_market_brief 表运行 |
| **M5 月度回测 + 报告产出** | D+12 | E2-S4/S5 完成,首份月度报告产出 |
| **M6 文档同步 + 收尾** | D+13 | E6 完成,所有项目索引文档更新 |

> 设计冻结日 = PRD 评审通过日,假定 2026-05-08(可调)

---

## 度量指标

### 业务指标(月度报告体现)

| 指标 | 目标 | 检查频率 |
|---|---|---|
| L8 v1 公式 vs B2(涨幅 Top 10)的 T+5 胜率差 | > +3pp(若 ≤ 0,说明现有公式无价值) | 月度 |
| L8 v1 vs B0(随机)的 T+5 胜率差 | > +5pp | 月度 |
| 4 类分类样本量平衡度 | 任一类别样本占比 < 70% | 月度 |
| 极端市况触发次数 | 记录,不设目标 | 月度 |

### 技术指标

| 指标 | 目标 | 检查频率 |
|---|---|---|
| schema 双写一致性 | 100% | 每日 |
| 标注表历史回填完整率 | T+5 字段 ≥ 95% | 一次性 |
| 标注表每日增量回填及时率 | T+1 在 09:30 前完成 | 每日 |
| 月度回测脚本运行成功率 | ≥ 99% | 月度 |
| 月度报告按时产出率 | 每月 1 号 03:00 前 | 月度 |

---

## 已锁定参数(2026-05-07 决议)

7 项参数已全部锁定,实施侧按以下值落地。后续若需调整,在 `IMPLEMENTATION_FEEDBACK.md` 记录变更原因和数据依据。

| ID | 内容 | 锁定值 | 影响范围 | 后续调整路径 |
|---|---|---|---|---|
| **TBD-1** | 极端市况涨停数阈值 | **100** | E4-S1 触发条件 | 跑满 60 个交易日后,根据 D 视图触发频率和体感反馈调整 |
| **TBD-2** | 历史回填范围 | **近 250 个交易日**(约 1 年) | E2-S2 工程量 | 实施侧确认数据完整性,如有缺失可缩短 |
| **TBD-3** | C3 资金驱动"北向资金异常"阈值 | **单日全市场净买 > 50 亿元**;个股层面阈值待 dim_yz_seat 录入完成后定 | E3-S1 分类逻辑 | 写入 `dim_signal_threshold` 配置表(若建)或硬编码,3 个月后回测调优 |
| **TBD-4** | C4 事件驱动颗粒度 | **不细分**(全集统一打标 C4) | F3 升级时再决定 | 月度报告若发现 C4 整体胜率异常或内部高分化,触发升级到 pos/neg/neutral 三档 |
| **TBD-5** | D 视图前端展示形态 | **后端只产数据**(`app_market_brief` 表) | 前端实现细节 | 前端形态由小程序自行决定,不在本 PRD 范围 |
| **TBD-6** | 评估系统数据库选型 | **纯 MySQL** | E2 性能 | 首次月度回测若 > 30 分钟,启动迁移到 ClickHouse 专用表 |
| **TBD-7** | F1 → F3 升级触发阈值 | **8pp**(分类胜率显著高于单一目标 8 个百分点) | 长期路线图 | 跑满 60 个交易日数据后实测,可调到 5-10pp |

---

## 扩展路径(留扩展位的具体落点)

第一版完成后,后续升级路线:

| 阶段 | 触发条件 | 要加的东西 | 已留的扩展位 |
|---|---|---|---|
| 阶段 2:加监控告警 | 跑满 60 个交易日,想要自动衰退预警 | 新建 `obs_strategy_health` 表 + 邮件告警 | 复用 obs_* 前缀和异动管线 v1.1 邮件框架 |
| 阶段 3:A/B 实验 | 想试新评分公式但不全量切 | 月度回测脚本里按 source_version 拆组对比 | source_version 字段一开始就在 |
| 阶段 4:F3 分类目标函数 | 评估报告显示分类胜率显著高于单一目标 8pp | 月度回测脚本加分类目标计算 | anomaly_category 一开始就标了 |
| 阶段 5:特征卡片 | 评分公式特征数 > 10 个,需要管理 | 新建 `dim_feature_card` 表 | component_score JSON 一直在记录每个特征贡献 |
| 阶段 6:分笔接入 | 阶段 4 后诊断显示假异动主要是出货式涨停 | 新增 `ads_stock_intraday_features` + tick_confidence 写入 component_score | component_score JSON 留好了写入位置 |
| 阶段 7:B 视图(训练) | 第 8 章训练系统投产 | 训练样本生成器(从 ads_l8_unified_signal 抽多样化样本) | anomaly_category 提供分类基础 |
| 阶段 8:C 视图(验证) | 第 9 章观察点系统投产 | 自动生成假设 + 跟踪标的池 | 异动数据 + obs_* 系统已就绪 |

> 每一步都是"加",不是"改"。保留迭代空间的工程纪律是 v1 设计的核心目的。

---

## 变更记录

| 日期 | 版本 | 变更 | 作者 |
|---|---|---|---|
| 2026-05-07 | v0.1 | 初稿,基于 17 轮设计讨论的极简版方向 | Claude 协助 |
| 2026-05-07 | v0.2 | 7 个 TBD 全部锁定:阈值 100 / C4 不细分 / 评估纯 MySQL / 其他接受默认 | Claude 协助 |
