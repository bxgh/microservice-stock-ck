# 每日复盘数据存储设计 (Daily Review Storage Specification) - V4 (腾讯云 MySQL 版)

本文件定义了“每日复盘”模块底层存储的物理架构规划。
**重大架构调整说明**：为了严格区分**原生行情数据**（海量的、原始的、读写密集的，适合存储在本地 ClickHouse）与**业务衍生数据**（高价值的、低频的、定性的，必须保证绝对安全持久化），本规划将所有“每日复盘”所产生的数据表全面迁移至**腾讯云 MySQL 数据库**中。

由于每日复盘产生的数据量极小（每年大约 250 行记录），使用 MySQL 的 `InnoDB` 引擎做主键关联不仅性能极速，更可以完美接入各类 BI 页面或后端微服务的关系型请求。

---

## 1. 核心表结构 (腾讯云 MySQL)

为了保持原子性，各个信号源分别独立建表，所有表的 `PRIMARY KEY` 统一规范为 `trade_date` (交易日期)。针对 ClickHouse 特有的嵌套类型（如 `Array` / `Map`），在 MySQL 中统一降维并采用原生 `JSON` 数据类型。

### 1.1 市场整体汇总表 (market_review_daily_summary)
```sql
CREATE TABLE IF NOT EXISTS market_review_daily_summary (
    trade_date DATE PRIMARY KEY COMMENT '交易日期',
    hs300_chg DECIMAL(10,4) COMMENT '沪深300涨跌幅',
    zz500_chg DECIMAL(10,4) COMMENT '中证500涨跌幅',
    zz1000_chg DECIMAL(10,4) COMMENT '中证1000涨跌幅',
    bz50_chg DECIMAL(10,4) COMMENT '北证50涨跌幅',
    up_count INT UNSIGNED COMMENT '上涨家数',
    down_count INT UNSIGNED COMMENT '下跌家数',
    limit_up_count INT UNSIGNED COMMENT '涨停家数',
    limit_down_count INT UNSIGNED COMMENT '跌停家数',
    market_amount DECIMAL(20, 2) COMMENT '全市场成交额',
    amount_z_score DECIMAL(10,4) COMMENT '成交额Z-Score',
    money_making_idx DECIMAL(10,4) COMMENT '赚钱效应系数',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='市场整体汇总基础表';
```

### 1.2 汇金特征表 (market_review_huijin)
```sql
CREATE TABLE IF NOT EXISTS market_review_huijin (
    trade_date DATE PRIMARY KEY COMMENT '交易日期',
    intensity DECIMAL(10,4) COMMENT '护盘强度(0-100)',
    etf_z_scores JSON COMMENT '宽基ETF放量Z-Score映射表(JSON)',
    avg_premium DECIMAL(10,4) COMMENT 'IOPV尾盘平均绝对溢价率',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='国家队(汇金)盘口干预特征表';
```
> **说明**：`etf_z_scores` 使用 JSON 存储，格式如 `{"510300": 3.42, "510500": 1.15}`。

### 1.3 机构资金表 (market_review_institution)
```sql
CREATE TABLE IF NOT EXISTS market_review_institution (
    trade_date DATE PRIMARY KEY COMMENT '交易日期',
    net_amount DECIMAL(20, 2) COMMENT '大单特大单净买入额',
    north_funds_net DECIMAL(20, 2) COMMENT '北向资金(陆股通)净流入额',
    active_stock_count INT UNSIGNED COMMENT '机构极度活跃标的数量',
    top_sectors JSON COMMENT '机构资金重点流入的前排行业列表(JSON数组)',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='机构及北向资金行为表';
```

### 1.4 游资热点表 (market_review_yousi)
```sql
CREATE TABLE IF NOT EXISTS market_review_yousi (
    trade_date DATE PRIMARY KEY COMMENT '交易日期',
    limit_success_rate DECIMAL(10,4) COMMENT '涨停封板成功率',
    limit_stairs JSON COMMENT '连板梯队分布(JSON,如{"1板":40,"2板":5})',
    top_concepts JSON COMMENT '当日常见且爆发的主流游资题材列表(JSON数组)',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='游资活跃度与题材梯队表';
```

### 1.5 量化行为表 (market_review_quant)
```sql
CREATE TABLE IF NOT EXISTS market_review_quant (
    trade_date DATE PRIMARY KEY COMMENT '交易日期',
    small_order_ratio DECIMAL(10,4) COMMENT '全市场小单成交额占比',
    t0_sell_pressure DECIMAL(10,4) COMMENT 'T0资金尾盘单边压盘抛压测度',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='量化T0抛压与微观行为表';
```

### 1.6 市场流动性与趋势表 (market_review_liquidity)
本表用于精准对接《每日复盘_成交量.md》中定义的六大核心流动性二阶导数测度方程式：
```sql
CREATE TABLE IF NOT EXISTS market_review_liquidity (
    trade_date DATE PRIMARY KEY COMMENT '交易日期',
    vol_ma_divergence DECIMAL(10,4) COMMENT 'VOL-01 成交额均线背离(动能差)',
    vol_rank DECIMAL(6,4) COMMENT 'VOL-01 日线成交额历史分值(Expanding Rank)',
    vol_ma5_rank DECIMAL(6,4) COMMENT 'VOL-01 5日均量历史分值(情绪极值)',
    vol_ma20_rank DECIMAL(6,4) COMMENT 'VOL-01 20日均量历史分值(牛熊底色)',
    vol_01_state VARCHAR(20) DEFAULT 'NORMAL' COMMENT 'VOL-01 状态机判定结果(如ACCEL_IN)',
    margin_velocity DECIMAL(10,4) COMMENT 'VOL-02 融资买入动量的占比加速度',
    congestion_velocity DECIMAL(10,4) COMMENT 'VOL-03 极值拥挤度的加速度(前10%虹吸比)',
    zombie_stock_derivation DECIMAL(10,4) COMMENT 'VOL-04 极寒无流动性股衍生率(Z-Score)',
    cost_pulse_fdr007 DECIMAL(10,4) COMMENT 'VOL-05 资金成本的异常脉冲(FR007)',
    non_bank_premium DECIMAL(10,4) COMMENT 'VOL-05 辅助非银流动性溢价(R007-FR007)',
    etf_depletion_rate DECIMAL(10,4) COMMENT 'VOL-06 ETF被动护盘的效用消耗斜率',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='全市场微观与宏观流动性二阶趋势表';
```

---

## 2. API 与数据访问视图层 (View)

为了便于微服务一次性抓取某天的全量复盘结论，我们在腾讯云 MySQL 内部创建一个极简的联合读视图。

```sql
CREATE OR REPLACE VIEW view_market_daily_review AS
SELECT 
    s.*, 
    h.intensity, h.avg_premium, 
    i.net_amount AS inst_net_amount, 
    y.limit_success_rate, 
    q.small_order_ratio,
    l.vol_ma_divergence, l.vol_rank, l.vol_ma5_rank, l.vol_ma20_rank, l.vol_01_state, l.margin_velocity, l.congestion_velocity, l.zombie_stock_derivation, l.cost_pulse_fdr007, l.non_bank_premium, l.etf_depletion_rate
FROM market_review_daily_summary s
LEFT JOIN market_review_huijin h ON s.trade_date = h.trade_date
LEFT JOIN market_review_institution i ON s.trade_date = i.trade_date
LEFT JOIN market_review_yousi y ON s.trade_date = y.trade_date
LEFT JOIN market_review_quant q ON s.trade_date = q.trade_date
LEFT JOIN market_review_liquidity l ON s.trade_date = l.trade_date;
```

## 3. 存储迁移架构准则

1.  **高可用边界隔离**：将极高频的基础 Tick/K 线等机器识别数据严格保留在 ClickHouse 中；将提取、降配后可供策略层低频直接查询甚至由人类阅览分析的高价值衍生数据（复盘数据）全部写入腾讯云 MySQL 面向应用层。
2.  **写放宽/读合并**：各个数据的聚合计算模块（无论是算汇金的、游资的还是成交量流动的）由于发生时间和计算资源各异，可分开按表分批写入、独立落盘，最终在业务层依靠主键级联读取视图。
