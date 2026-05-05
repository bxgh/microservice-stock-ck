# Epic 3: 分层监测架构与业务服务

## 目标
将单一计算逻辑扩展到全市场、行业、风格等不同维度。

## Stories

### Story 3.1: 分层模型抽象
- **实现**：`src/layers/base.py`。定义不同 Layer 的输入（股票池）和输出（计算结果）。

### Story 3.2: 核心监控层 (L1-L3)
- **L1 (Market)**: 全市场（如中证全指成分）。
- **L2 (Style)**: 价值/成长/大小盘。
- **L3 (Industry)**: 申万一级行业。

### Story 3.3: 每日计算服务 (DailyService)
- **实现**：`src/services/daily_service.py`。
- **流程**：获取成分股 -> 并发拉取数据 -> 计算各层 CCI -> 写入数据库。
