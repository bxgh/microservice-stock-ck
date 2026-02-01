#!/usr/bin/env python3
"""
Job: ai_quality_gatekeeper.py
功能：AI 智能判决异常股票
输入：JSON 字符串 (包含 abnormal list)
输出：JSON 字符串 (包含 confirmed_bad_codes)
"""

import asyncio
import logging
import sys
import json
import argparse
import os
from pydantic import BaseModel, Field
from typing import List

# 调整 path 以导入 gsd_agent
current_dir = os.path.dirname(os.path.abspath(__file__))
# 假设 gsd-worker/src/jobs -> gsd-worker/src -> libs/gsd-agent/src is needed?
# 实际上 libs 已在 PYTHONPATH 中 (见 tasks.yml global config)
# 如果 gsd_agent 安装在环境里则直接导入
from gsd_agent.core import SmartDecisionEngine
from gsd_agent.core.prompts import PromptManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AI_Gatekeeper")

class AnomalyVerdict(BaseModel):
    code: str
    is_data_issue: bool = Field(..., description="True if this is a system failure, False if it is valid market behavior")
    reason: str

class AuditResult(BaseModel):
    verdicts: List[AnomalyVerdict]

async def main():
    parser = argparse.ArgumentParser(description="AI 智能质量门禁")
    # Support both old --quality-report and new workflow arguments
    parser.add_argument("--quality-report", type=str, help="Legacy: Abnormal list JSON string/Report")
    parser.add_argument("--input-data", type=str, help="Workflow: Abnormal list (JSON)")
    parser.add_argument("--trigger-condition", type=str, default="AI_AUDIT", help="Workflow: Trigger Condition (Action)")
    
    args = parser.parse_args()

    # 0. 检查触发条件
    if args.trigger_condition == "FAILOVER":
        logger.warning(f"🔴 触发 FAILOVER 模式，跳过 AI 直接进入全量补采...")
        # FAILOVER 模式下，直接输出 full 模式和高并发配置
        output = {
            "confirmed_bad_codes": [], 
            "repair_mode": "full", 
            "repair_concurrency": 60,
            "decision": "FAILOVER_ACCELERATION"
        }
        print(f"GSD_OUTPUT_JSON: {json.dumps(output)}")
        return

    if args.trigger_condition and args.trigger_condition not in ["REPAIR", "AI_AUDIT"]:
        logger.info(f"⏭️ 触发条件不满足 ({args.trigger_condition})，且非 FAILOVER，跳过执行。")
        output = {
            "confirmed_bad_codes": [], 
            "repair_mode": "skip", 
            "repair_concurrency": 0,
            "decision": "CONDITION_NOT_MET"
        }
        print(f"GSD_OUTPUT_JSON: {json.dumps(output)}")
        return

    try:
        # 1. 解析输入
        raw_input = args.input_data or args.quality_report
        if not raw_input:
            # Empty input -> No abnormalities
            print("GSD_OUTPUT_JSON: {\"confirmed_bad_codes\": []}")
            return

        # Deal with potential "{{ ... }}" liquid artifacts if raw_input was not properly substituted? 
        # (Assuming Orchestrator handles it, but safe to strip)
        if raw_input.startswith("{{") and raw_input.endswith("}}"):
            logger.warning("⚠️ 输入看起来像是未替换的模板变量，视为无效输入")
            print("GSD_OUTPUT_JSON: {\"confirmed_bad_codes\": []}")
            return

        report = json.loads(raw_input)
        
        # 兼容不同格式：直接是 list，或者是包含 abnormal_list/missing_list 的 dict
        abnormal_list = []
        missing_list = []
        if isinstance(report, list):
            abnormal_list = report
        elif isinstance(report, dict):
            # 尝试从 report 根部或内置 dict 提取
            missing_list = report.get("missing_list", [])
            abnormal_list = report.get("abnormal_list", [])
            
            # 嵌套格式兼容 (Diagnosis 结构)
            diag = report.get("diagnosis", {})
            if isinstance(diag, dict):
                if not missing_list: missing_list = diag.get("missing_list", [])
                if not abnormal_list: abnormal_list = diag.get("abnormal_list", [])
        
        # 确定性故障：missing_list (已经完全缺失的肯定要补)
        mandatory_bad = list(set(missing_list))
        
        if not abnormal_list:
            if mandatory_bad:
                logger.info(f"📍 发现 {len(mandatory_bad)} 只缺失股票，无需 AI 审核直接进入补采。")
                output = {
                    "confirmed_bad_codes": mandatory_bad,
                    "repair_mode": "repair",
                    "repair_concurrency": 20,
                    "decision": "MANDATORY_REPAIR"
                }
            else:
                logger.info("✅ 没有发现异常记录，审核通过。")
                output = {
                    "confirmed_bad_codes": [],
                    "repair_mode": "skip",
                    "repair_concurrency": 0,
                    "decision": "ALL_CLEAR"
                }
            print(f"GSD_OUTPUT_JSON: {json.dumps(output)}")
            return

        logger.info(f"🧠 AI 介入审核 {len(abnormal_list)} 只异常股票...")
        
        # 2. 初始化 AI
        engine = SmartDecisionEngine(
            api_keys={
                "siliconflow": (os.getenv("SILICONFLOW_API_KEY") or "").strip(),
                "deepseek": (os.getenv("DEEPSEEK_API_KEY") or "").strip()
            },
            redis_url=os.getenv("GSD_REDIS_URL", "redis://localhost:6379/0"),
            default_provider="siliconflow",
            default_model="deepseek-ai/DeepSeek-V3"
        )
        
        # 添加 Prompt
        engine.prompts = PromptManager({
            "post_market_anomaly_audit": """
You are a Financial Data Quality Auditor for China A-Share Market.
Your job is to analyze data anomalies identified by the automated resilience check.

Context:
- Market: China A-Share (Post-close analysis)
- Abnormal Stocks: {{ abnormal_list }}

Task: 
Analyze each stock to determine if the anomaly represents a SYSTEM DATA FAILURE (Data Issue) or VALID MARKET BEHAVIOR (Market Issue).

Analysis Rules:
1. **Low Tick Count / Volume Mismatch**: 
   - Verify if the stock is SUSPENDED (停牌) or ST status with Limit Up/Down (涨跌停). 
   - If Suspended/Limit Up/Down -> Likely VALID (Not a data issue).
   - If Liquid stock & Low ticks/Mismatch -> Likely DATA ISSUE.
2. **Missing Data**:
   - Almost always a DATA ISSUE unless suspended for a long time.

Output specific JSON format:
{
    "verdicts": [
        {
            "code": "stock_code",
            "is_data_issue": true/false,
            "reason": "Brief analysis (e.g., 'Stock is suspended', 'Liquid stock missing data')"
        }
    ]
}
"""
        })

        # 3. 批量处理 (为了节省 Token，一次性发给 LLM，如果列表太长需要分批)
        # 限制处理数量以避免 Token 溢出，对于 A 股，通常异常股票不会太多
        # 如果太多，只审前 50 只作为采样，或者直接判决。
        max_audit = 50
        target_list = abnormal_list
        if isinstance(abnormal_list, list) and len(abnormal_list) > max_audit:
            logger.warning(f"⚠️ 异常数量过多 ({len(abnormal_list)})，AI 仅审核前 {max_audit} 只")
            target_list = abnormal_list[:max_audit]
        
        simplified_input = json.dumps(target_list)

        result: AuditResult = await engine.run(
            prompt_template="post_market_anomaly_audit",
            inputs={"abnormal_list": simplified_input},
            response_model=AuditResult,
            priority="fast" # Use fast model (likely siliconflow/qwen) to avoid default model mismatch
        )

        # 4. 提取确认为错误的股票
        ai_confirmed_bad = []
        for v in result.verdicts:
            logger.info(f"🤖 Code {v.code}: {v.is_data_issue} ({v.reason})")
            if v.is_data_issue:
                ai_confirmed_bad.append(v.code)
        
        # [Critical Fix] 合并确定性缺失 (mandatory_bad) 和 AI 判定异常
        # 确保只要缺失就必补，不论 AI 如何判定
        final_confirmed = list(set(mandatory_bad + ai_confirmed_bad))
        
        if len(final_confirmed) > len(ai_confirmed_bad):
            logger.info(f"➕ 已自动合并 {len(final_confirmed) - len(ai_confirmed_bad)} 只确定性缺失股票")

        # 5. 输出结果
        output = {
            "reviewed_count": len(abnormal_list),
            "confirmed_bad_codes": final_confirmed,
            "repair_mode": "repair" if final_confirmed else "skip",
            "repair_concurrency": 20 if final_confirmed else 0,
            "decision": "AI_AUDIT_DONE"
        }
        print(f"GSD_OUTPUT_JSON: {json.dumps(output)}")

    except Exception as e:
        logger.error(f"❌ AI 审核异常终止: {e}")
        # 容错降级逻辑: 如果 AI 无法判定，退而求其次
        # 直接输出所有输入的异常代码进行强制补采，确保数据不丢失，但严禁扩大范围。
        # 注意: 这里假设 abnormal_list 已经在上方解析成功。
        confirmed = abnormal_list if 'abnormal_list' in locals() else []
        logger.warning(f"⚠️ AI 降级：全量放行 {len(confirmed)} 只异常股票进入补采阶段。")
        output = {
            "confirmed_bad_codes": confirmed,
            "repair_mode": "repair" if confirmed else "skip",
            "repair_concurrency": 20 if confirmed else 0,
            "decision": "FALLBACK_TO_MANUAL"
        }
        print(f"GSD_OUTPUT_JSON: {json.dumps(output)}")
        sys.exit(0) # 保持 Workflow 继续

if __name__ == "__main__":
    asyncio.run(main())
