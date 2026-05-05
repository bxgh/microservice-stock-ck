import os
import logging
from typing import Dict, Any, List
import pandas as pd

from gsd_agent.core import SmartDecisionEngine
from gsd_agent.core.prompts import PromptManager
from .ai_schemas import AIAnalysisResult

logger = logging.getLogger(__name__)

class AIInterpreter:
    """
    AI 智能解读器
    将 9 维特征及其分布结果转换为深度研报见解
    """
    
    def __init__(self):
        self.api_key = os.getenv("SILICONFLOW_API_KEY", "").strip()
        self.redis_url = os.getenv("QS_REDIS_URL", "redis://localhost:6379/0")
        
        if not self.api_key:
            logger.warning("⚠️ SILICONFLOW_API_KEY not found. AI interpretation may fail.")
        else:
            logger.info(f"🔑 AIInterpreter initialized with key: {self.api_key[:10]}...")
            
        self.engine = SmartDecisionEngine(
            api_keys={"siliconflow": self.api_key},
            redis_url=self.redis_url,
            default_provider="siliconflow",
            default_model="deepseek-ai/DeepSeek-V3"
        )
        
        self.engine.prompts = PromptManager({
            "feature_interpretation": """
你是一名资深的 A 股盘口分析专家（Quant Trader）。
你的任务是根据给出的股票【9维高频特征矩阵】的排名和分位点数据，给出一份专业的、有深度的 AI 解读报告。

### 背景知识：特征含义
- f1 (主动强度): 主动买入强度 (Lee-Ready)
- f2 (OBI): 盘口买卖挂单失衡度
- f3 (收益率): 当日累积收益率变化
- f4 (LOR): 机构大单成交占比
- f5 (NLB): 机构净买入金额 (Net Large Buy)
- f6 (NLB_Ratio): 机构净买入占比
- f7 (RID): 散户/机构行为背离度
- f8 (VPIN): 订单流毒性（知情交易概率，越高代表卖盘越犀利/消息面影响大）
- f9 (Lambda): Kyle's Lambda (冲击成本/市场深度，越高代表滑点越大/承接越差)

### 目标股票数据:
- 代码: {{ code }}
- 名称: {{ name }}
- 行业: {{ industry }}
- 本次对标样本数: {{ peer_count }}

### 维度统计 (分位值越高代表该指标在同行中越强):
{{ feature_stats }}

### 综合排名:
{{ ranking_info }}

### 要求:
1. **不要复现数字**，要从多变量组合的角度分析“资金在干什么”。
2. **重点关注极端分位值**（<20% 或 >80%）。
3. 如果 f8 (VPIN) 极高而 f1 (强度) 极低，注意是否存在潜在的内幕利空抛压。
4. 如果 f4/f5 (机构) 极高而股价下跌，注意是否存在护盘或潜伏吸筹。
5. 请使用专业、严谨、冷峻的量化分析语言。

输出必须为符合以下 JSON 结构的格式（不要包含 markdown 代码块标记）：
{
  "summary": "核心综述...",
  "insights": [
    {"feature_id": "f1", "observation": "...", "implication": "..."},
    ...
  ],
  "regime": {"regime_name": "...", "confidence": 0.8, "description": "..."},
  "advice": {"action": "...", "reason": "..."}
}
"""
        })

    async def interpret(
        self,
        target_info: Dict[str, Any],
        distribution: Dict[str, Any],
        ranking: Dict[str, Any],
        peer_count: int
    ) -> AIAnalysisResult | None:
        """
        运行 AI 解读
        """
        if not self.api_key:
            return None
            
        try:
            # 简化数据以减小 Context
            # 获取最新日期的分布
            latest_date = sorted(distribution.keys())[-1] if distribution else None
            if not latest_date:
                return None
                
            stats_str = ""
            for feat, pct in distribution[latest_date].items():
                stats_str += f"- {feat}: 分位点 {pct:.1f}%\n"
                
            rankings_str = ""
            rank_date = sorted(ranking.keys())[-1] if ranking else None
            if rank_date:
                data = ranking[rank_date]
                for feat, r_str in data.get('rankings', {}).items():
                    # r_str is e.g. "5/31"
                    rankings_str += f"- {feat}: {r_str}\n"

            inputs = {
                "code": target_info.get("code"),
                "name": target_info.get("name"),
                "industry": target_info.get("industry"),
                "peer_count": peer_count,
                "feature_stats": stats_str,
                "ranking_info": rankings_str
            }
            
            result: AIAnalysisResult = await self.engine.run(
                prompt_template="feature_interpretation",
                inputs=inputs,
                response_model=AIAnalysisResult,
                priority="fast"
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"AI Interpretation failed: {e}")
            return None
