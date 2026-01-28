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
    if args.trigger_condition and args.trigger_condition != "AI_AUDIT":
        logger.info(f"⏭️ 触发条件不满足 ({args.trigger_condition} != AI_AUDIT)，跳过 AI 审核。")
        print("GSD_OUTPUT_JSON: {\"confirmed_bad_codes\": []}")
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
        
        # 兼容不同格式：直接是 list，或者是包含 abnormal_list 的 dict
        abnormal_list = []
        if isinstance(report, list):
            abnormal_list = report
        elif isinstance(report, dict):
            # 尝试从 diagnosis.abnormal_list 或 abnormal_list 提取
            diag = report.get("diagnosis", {})
            if isinstance(diag, dict):
                abnormal_list = diag.get("abnormal_list", [])
            if not abnormal_list:
                abnormal_list = report.get("abnormal_list", [])
        
        if not abnormal_list:
            logger.info("✅ 没有发现异常记录，审核通过。")
            print("GSD_OUTPUT_JSON: {\"confirmed_bad_codes\": []}")
            return

        logger.info(f"🧠 AI 介入审核 {len(abnormal_list)} 只异常股票...")
        
        # 2. 初始化 AI
        engine = SmartDecisionEngine(
            api_keys={
                "siliconflow": os.getenv("SILICONFLOW_API_KEY"),
                "deepseek": os.getenv("DEEPSEEK_API_KEY")
            },
            redis_url=os.getenv("GSD_REDIS_URL", "redis://localhost:6379/0"),
            default_provider="siliconflow",
            default_model="deepseek-ai/DeepSeek-V3"
        )
        
        # 添加 Prompt
        engine.prompts = PromptManager({
            "post_market_anomaly_audit": """
You are a Financial Data Quality Auditor.
Review the following list of stocks with suspiciously low tick counts for today (Normal is ~4800).
Determine if the low count is due to a DATA COLLECTION FAILURE (System Error) or VALID MARKET BEHAVIOR (e.g., Trading Suspension, Limit Up/Down with low volume).

Current Context:
- Market: China A-Share
- Time: Post-close
- Abnormals: {{ abnormal_list }}

Rules:
1. If the stock is typically liquid but has very few ticks, suspect Data Failure.
2. If the stock is known to be suspended or ST with limit up/down, it might be Valid.
3. Use your knowledge base to infer status.

Output a JSON object strictly following this schema:
{
    "verdicts": [
        {
            "code": "stock_code",
            "is_data_issue": true/false,
            "reason": "explanation"
        },
        ...
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
        confirmed_bad = []
        for v in result.verdicts:
            logger.info(f"🤖 Code {v.code}: {v.is_data_issue} ({v.reason})")
            if v.is_data_issue:
                confirmed_bad.append(v.code)

        # 5. 输出结果
        output = {
            "reviewed_count": len(abnormal_list),
            "confirmed_bad_codes": confirmed_bad
        }
        print(f"GSD_OUTPUT_JSON: {json.dumps(output)}")

    except Exception as e:
        logger.error(f"❌ AI 审核失败: {e}", exc_info=True)
        # Fallback: 如果 AI 挂了，保守起见认为所有异常都是坏的？或者都不修？
        # 策略：Fail-safe -> Assume all are bad (repair everything) OR Assume none (skip)
        # 这里选择 fallback 到全部修，宁滥勿缺
        # print(json.dumps({"confirmed_bad_codes": [item['code'] for item in json.loads(args.input_data)]}))
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
