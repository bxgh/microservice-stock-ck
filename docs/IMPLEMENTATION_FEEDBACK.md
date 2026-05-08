# 实施反馈全局索引 (Implementation Feedback Index)

本文件作为内网仓实施进度的全局索引。详细的实施计划、任务列表及验收报告请查看对应 Story 的子目录。

目录规范: `docs/implementation_logs/E{N}/S{M}/`

| 日期 | Story ID | 摘要 | 详细日志路径 | 状态 |
|---|---|---|---|---|
| 2026-05-06 | - | 初始化全局索引 | - | DONE |
| 2026-05-06 | E1-S1 | 派生指标层表结构实施 | docs/design/异动股捕捉/implementation_logs/E1/S1/ | DONE |
| 2026-05-06 | E1-S2 | 异动信号统一池表实施 | docs/design/异动股捕捉/implementation_logs/E1/S2/ | DONE |
| 2026-05-06 | E1-S3 | 标签字典与关系表实施 | docs/design/异动股捕捉/implementation_logs/E1/S3/ | DONE |
| 2026-05-06 | E1-S4 | 筛选模板表实施 | docs/design/异动股捕捉/implementation_logs/E1/S4/ | DONE |
| 2026-05-06 | E1-S5 | 市场状态表实施 | docs/design/异动股捕捉/implementation_logs/E1/S5/ | DONE |
| 2026-05-06 | E1-S6 | Top 10 推送清单表实施 | docs/design/异动股捕捉/implementation_logs/E1/S6/ | DONE |
| 2026-05-06 | E1-S7 | 评分权重配置表实施 | docs/design/异动股捕捉/implementation_logs/E1/S7/ | DONE |
| 2026-05-06 | E1-S8 | 用户板块偏好表实施 | docs/design/异动股捕捉/implementation_logs/E1/S8/ | DONE |
| 2026-05-06 | E1-S9 | 元数据初始化实施 | docs/design/异动股捕捉/implementation_logs/E1/S9/ | DONE |
| 2026-05-07 | E2-S1 | 盘后分笔同步作业编排与稳定性治理 | docs/分笔数据/盘后全市场同步/implementation_logs/E2/S1/ | DONE |
| 2026-05-07 | E3-S1 | 盘后一致性审计 (Gate-3) 实施 | docs/分笔数据/盘后全市场同步/implementation_logs/E3/S1/ | DONE |
| 2026-05-07 | Doc Align | 对齐 stock_kline_daily 表名与 volume (股) 单位 | docs/分笔数据/盘后全市场同步/01_DATA_SCHEMA.md | DONE |
| 2026-05-08 | E1-S1 | 异动捕捉主表增量改造 (极简版 v1) | docs/design/异动股捕捉/implementation_logs/E1/S1/ | DONE |

| 2026-05-08 | E1-S2 | 激活评分权重版本化使用 | docs/design/异动股捕捉/implementation_logs/E1/S2/ | DONE |
| 2026-05-08 | E2-S1 | 评估标注表建表 (MySQL + ClickHouse) | docs/design/异动股捕捉/implementation_logs/E2/ | DONE |
| 2026-05-08 | E3-S1 | 异动分类 (C1-C4) 与评分溯源实施 | docs/design/异动股捕捉/implementation_logs/E3/S1/ | DONE |
| 2026-05-08 | E4-S1 | 极端市况门控 (熔断) 与 D 视图实施 | docs/design/异动股捕捉/implementation_logs/E4/S1/ | DONE |
| 2026-05-08 | E5-S1 | 系统集成与项目文档同步 (v1.1 极简版收官) | docs/design/异动股捕捉/implementation_logs/E5/S1/ | DONE |

### 跨仓 Schema 变更记录
- [2026-05-08] 跨仓 schema 变更: `ads_l8_unified_signal` (Node-41 MySQL → Node-41 ClickHouse) - 已完成
- [2026-05-08] 跨仓 schema 变更: `ads_l8_backtest_label` (Node-41 MySQL → Node-41 ClickHouse) - 已完成
- [2026-05-08] 跨仓 schema 变更: `app_market_brief` (Node-41 MySQL → 云端 MySQL) - [NEW] 待同步
