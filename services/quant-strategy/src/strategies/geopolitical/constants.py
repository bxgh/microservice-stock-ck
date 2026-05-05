"""
地缘冲突策略常量定义 (EPIC-019)
"""

from enum import Enum

class ScenarioType(Enum):
    IDLE = "IDLE"           # 战争未开始或已结束
    SCENARIO_A = "FLASH"    # 闪电战 (初期冲击)
    SCENARIO_B = "MEDIUM"   # 中度冲突 (僵持期)
    SCENARIO_C = "LONG"     # 持久战 (全面防御)

# 战争关键参数
WAR_START_DATE = "2026-03-01"  # 本次模拟确定的起始日
BASE_INDEX = "000300.SH"       # 沪深300指数作为市场基准
BASE_OIL = "CL"                # WTI原油期货作为能源风险基准

# 场景切换时间阈值 (天数)
THRESHOLD_DAYS_A_B = 14  # A转B: 2周
THRESHOLD_DAYS_B_C = 90  # B转C: 3个月

# 市场触发阈值 (跌幅/涨幅) - 情景A启动门槛
# 如果战争已开始但市场波动不足，可能维持 IDLE 或弱 A
TRIGGER_INDEX_DROP = -0.03     # 指数累计跌幅超过 3%
TRIGGER_OIL_SURGE = 0.10       # 原油累计涨幅超过 10%

# 权重配置 (可在更高级别 YAML 中覆盖)
SCENARIO_WEIGHTS = {
    ScenarioType.SCENARIO_A: {
        "excess_return": 0.4,
        "max_drawdown": 0.2,
        "concept_score": 0.3,
        "fundamental": 0.1
    },
    ScenarioType.SCENARIO_B: {
        "excess_return": 0.3,
        "max_drawdown": 0.2,
        "concept_score": 0.2,
        "fundamental": 0.3
    },
    ScenarioType.SCENARIO_C: {
        "excess_return": 0.2,
        "max_drawdown": 0.1,
        "concept_score": 0.1,
        "fundamental": 0.6  # 持久战极度重视基本面与分红
    }
}

# 防御性板块定义 (关键字)
DEFENSIVE_SECTORS = ["石油", "黄金", "国防军工", "军工", "航天", "种植业", "农业", "粮食", "煤炭", "燃气"]

