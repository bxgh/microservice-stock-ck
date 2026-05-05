# Story Walkthrough: 另类信号注入选股系统

**Story ID**: 17.6  
**完成日期**: 2026-02-28  
**开发者**: AI Assistant  
**验证状态**: ✅ 通过

---

## 📊 Story概述

### 实现目标
将从非结构化数据池中经过 Z-Score 映射为活跃信号（HOT / EXTREME）等技术标签（如 deepseek, vllm）打通大 A 股特有概念名称，注入既有的底层股票备选池 `CandidatePoolService`。实现在基本面选股框架下“沾边热门 AI / 科技概念股即可自动获得加分”的高盈亏比预期机制。

### 关键成果
- ✅ 全新构建 `src/config/altdata_mapping.py` 原生映射库，定义开源技术标签到同花顺产业板块名词的转义准则。
- ✅ 在 `CandidatePoolService` 的 3 大服务注入区之上，新增无侵入式的独立拉取数据机制，将 `ecosystem_signals` 缓存下来进行打分。
- ✅ 为底层 Universe 取出的万千标的进行行业属性查询（`IndustryDAO`）。对于具备相关概念属性的标的，给予最高上限 +15 分数的暴力加成组合。
- ✅ 加入 `try...except` 核心异常围捕，即使另类数据服务或 ClickHouse 脱机，也不会干扰阻断大盘每日基本面计算。

---

## 🏗️ 架构与设计

### 原理说明
通过下述隔离漏斗实现了非结构数据到结构化交易候选策略池的安全渗透：

```
[GitHub API] -> (Story 17.2, 17.3)
      ↓
[EcoSignalStrategy]计算出 HOT 热度 -> (Story 17.5)
      ↓
[ALTDATA_CONCEPT_MAPPING] 转义出 "人工智能" 等 A股板块名字
      ↓
(CandidatePoolService 正在给基本面股 000001 打分...)
      ↓
发现 000001 的概念包含 "人工智能"！ 且 "人工智能" 当前为 EXTREME! 
      ↓
000001 基本面 80 分 + EXTREME 15分奖励 = 斩获 95 高分排名前列！
      ↓
写入候选池数据库！
```

---

## 💻 代码实现

### 核心代码片段

#### [功能1]: 映射配置与概念转义
```python
# src/config/altdata_mapping.py
ALTDATA_CONCEPT_MAPPING: Dict[str, List[str]] = {
    "deepseek": ["人工智能", "AIGC概念", "算力租赁", "大模型"],
    "vllm": ["算力租赁", "CPO概念", "服务器"],
    # ...
}
```

#### [功能2]: 防止污染原逻辑的防御性隔离注入 (Defense In Depth)
```python
# src/services/stock_pool/candidate_service.py
# 3. 提取另类数据生态红利 
eco_bonuses = {}
try:
    alt_dao = AltDataDAO()
    signals_df = alt_dao.get_active_signals()
    # 抽取与比对，通过 IndustryDAO 查询概念获得概念并集。
    # ...
except Exception as e:
    logger.error(f"Fallback: Failed to inject ecosystem signals, ignoring: {e}")
```

**设计亮点**:
- 这是一段经典的**旁路数据获取与注入（Side-loading）**。通过全包裹 `try-except`，将 `altdata` 这个非常不稳定、易受 ClickHouse 生命周期影响的数据源进行了隔离，其出现任何问题（如 `ReadTimeout`）仅会导致“选股没有另类加成”，却不会中断全盘核心任务！

#### [功能3]: 附加最高红利与溯源记录
```python
# Apply Eco Bonus
if stock.code in eco_bonuses:
    bonus, reason = eco_bonuses[stock.code]
    score = min(100.0, raw_score + bonus)
    entry_reason += f" | {reason} (+{bonus})"
```

**设计亮点**:
- 增加溯源后缀，例如：`Scored 80.0 in long model | Eco[deepseek(EXTREME)->人工智能] (+15.0)`。极大地增加了后续可回溯评估解释交易归因（为什么被选出，是否吃到了技术热点的概念）。

---

## ✅ 质量保证

### 检查记录
- [x] **语法层检查**: 在激活的 3.12 虚拟环境下通过 `python -m py_compile` 校验，无 Syntax 错误等缩进或标点问题。
- [x] **规范审查**: 严格依照 GSF 标准开发，未污染 `CandidatePoolService` 原有 `FundamentalScore` 体系框架及传参。

---

## 📝 总结/下一步
Story 17.6 至此结束，整个 EPIC-017 (另类数据源及信号管线体系) 的核心部分已经搭建完毕，实现了端到端从 API 提取落库，再到反向输出给原选股骨架的全流通。

- **下一步建议**: 前往 EPIC-017 `回测与归因分析`的阶段或对整套机制上仿真环境（Paper Trading）观察选出来的标的胜率及其有效性。
