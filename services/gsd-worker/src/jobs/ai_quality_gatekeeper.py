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
import pymysql
from dotenv import load_dotenv
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
    # 尝试加载根目录的 .env
    base_env = os.path.join(current_dir, "../../../../.env")
    if os.path.exists(base_env):
        load_dotenv(base_env)
    else:
        load_dotenv()
        
    parser = argparse.ArgumentParser(description="AI 智能质量门禁")
    # Support both old --quality-report and new workflow arguments
    parser.add_argument("--quality-report", type=str, help="Legacy: Abnormal list JSON string/Report")
    parser.add_argument("--input-data", type=str, help="Workflow: Abnormal list (JSON)")
    parser.add_argument("--input-file", type=str, help="Workflow: Batch input file path (JSON)")
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
        # 1. 解析输入 (优先读取文件以避免 Argument list too long)
        raw_input = None
        if args.input_file and os.path.exists(args.input_file):
            try:
                with open(args.input_file, 'r', encoding='utf-8') as f:
                    raw_input = f.read()
                logger.info(f"📂 从文件加载输入数据: {args.input_file} ({len(raw_input)} bytes)")
            except Exception as e:
                logger.error(f"❌ 读取输入文件失败: {e}")
        
        if not raw_input:
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
        
        # 1.1 获取停牌信息 (外部客观数据源)
        suspended_codes = set()
        target_date = report.get("target_date")
        if target_date:
            try:
                db_date = target_date
                if "-" not in db_date and len(db_date) == 8:
                    db_date = f"{db_date[:4]}-{db_date[4:6]}-{db_date[6:]}"
                
                host = os.getenv("MYSQL_HOST")
                port = int(os.getenv("MYSQL_PORT") or 3306)
                conn = pymysql.connect(
                    host=host,
                    port=port,
                    user=os.getenv("MYSQL_USER"),
                    password=os.getenv("MYSQL_PASSWORD"),
                    database=os.getenv("MYSQL_DATABASE") or os.getenv("MYSQL_DB")
                )
                try:
                    with conn.cursor() as cursor:
                        sql = "SELECT ts_code FROM stock_suspensions WHERE trade_date = %s"
                        cursor.execute(sql, (db_date,))
                        rows = cursor.fetchall()
                        for (raw_code,) in rows:
                            # 归一化代码: '000670.SZ' -> '000670'
                            clean_code = raw_code.split('.')[0]
                            suspended_codes.add(clean_code)
                    logger.info(f"📊 从数据库获取到 {len(suspended_codes)} 只停牌股票数据 ({db_date})")
                finally:
                    conn.close()
            except Exception as e:
                logger.error(f"❌ 获取停牌信息失败: {e}")

        # 1.2 过滤与分类
        # 确定性故障：missing_list (已经完全缺失的肯定要补，除非明确停牌)
        effective_missing = [c for c in missing_list if c not in suspended_codes]
        mandatory_bad = list(set(effective_missing))
        
        # 待研判列表：abnormal_list (也需要剔除明确停牌的，因为停牌会导致 tick 数异常)
        effective_abnormal = [c for c in abnormal_list if c not in suspended_codes]
        
        if len(suspended_codes) > 0:
            filtered_count = (len(missing_list) - len(effective_missing)) + (len(abnormal_list) - len(effective_abnormal))
            if filtered_count > 0:
                logger.info(f"🛡️ 自动过滤 {filtered_count} 只因停牌导致的异常申报")

        if not effective_abnormal:
            # [Fix] 如果没有待研判列表，但有确定性缺失，或者触发了 FAILOVER (即异常数很多)
            if mandatory_bad:
                logger.info(f"📍 发现 {len(mandatory_bad)} 只缺失股票，无需 AI 审核直接进入补采。")
                output = {
                    "confirmed_bad_codes": mandatory_bad,
                    "repair_mode": "repair",
                    "repair_concurrency": 20,
                    "decision": "MANDATORY_REPAIR"
                }
            elif args.trigger_condition == "FAILOVER":
                # 防御性逻辑：如果是监控到 FAILOVER 信号但列表为空 (可能被审计程序清空)
                # 依然维持 FULL 模式决策
                logger.warning(f"⚠️ 处于 FAILOVER 状态但收到空列表，维持全量修复决策。")
                output = {
                    "confirmed_bad_codes": [], 
                    "repair_mode": "full", 
                    "repair_concurrency": 60,
                    "decision": "FAILOVER_ACCELERATION"
                }
            else:
                # 检查统计数据，如果统计显示有大量缺失但列表为空 (审计程序的熔断保护)
                stats = report.get("stats", {})
                missing_stat = stats.get("missing", 0)
                if missing_stat > 200:
                    logger.warning(f"⚠️ 统计显示有 {missing_stat} 只缺失，但列表为空。触发紧急全量修复。")
                    output = {
                        "confirmed_bad_codes": [],
                        "repair_mode": "full",
                        "repair_concurrency": 60,
                        "decision": "FAILOVER_ACCELERATION"
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
        
        # 构建更丰富的上下文
        ai_context = {
            "abnormal_list": effective_abnormal,
            "suspension_list": list(suspended_codes)[:100] # 仅传前 100 只作为知识参考，防止 Context 过长
        }
        
        # 添加 Prompt
        engine.prompts = PromptManager({
            "post_market_anomaly_audit": """
You are a Financial Data Quality Auditor for China A-Share Market.
Your job is to analyze data anomalies identified by the automated resilience check.

Context:
- Market: China A-Share (Post-close analysis)
- Abnormal Stocks: {{ abnormal_list }}
- Known Suspensions (Partial): {{ suspension_list }}

Task: 
Analyze each stock to determine if the anomaly represents a SYSTEM DATA FAILURE (Data Issue) or VALID MARKET BEHAVIOR (Market Issue).

Analysis Rules:
1. **Low Tick Count / Volume Mismatch**: 
   - Check if stock is in the Suspension List or ST status with Limit Up/Down. 
   - If Suspended/Limit Up/Down -> Likely VALID (Not a data issue).
2. **Missing Data**:
   - If not in suspension list but missing, almost always a DATA ISSUE.

Output specific JSON format:
{
    "verdicts": [
        {
            "code": "stock_code",
            "is_data_issue": true/false,
            "reason": "Brief analysis"
        }
    ]
}
"""
        })

        # 3. 批量处理 (为了节省 Token，一次性发给 LLM，如果列表太长需要分批)
        # 限制处理数量以避免 Token 溢出，对于 A 股，通常异常股票不会太多
        # 如果太多，只审前 50 只作为采样，或者直接判决。
        max_audit = 50
        target_list = effective_abnormal
        if isinstance(effective_abnormal, list) and len(effective_abnormal) > max_audit:
            logger.warning(f"⚠️ 异常数量过多 ({len(effective_abnormal)})，AI 仅审核前 {max_audit} 只")
            target_list = effective_abnormal[:max_audit]
        
        simplified_input = json.dumps(target_list)

        result: AuditResult = await engine.run(
            prompt_template="post_market_anomaly_audit",
            inputs=ai_context,
            response_model=AuditResult,
            priority="fast"
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
            "reviewed_count": len(effective_abnormal),
            "confirmed_bad_codes": final_confirmed,
            "repair_mode": "repair" if final_confirmed else "skip",
            "repair_concurrency": 20 if final_confirmed else 0,
            "decision": "AI_AUDIT_DONE"
        }
        print(f"GSD_OUTPUT_JSON: {json.dumps(output)}")

    except Exception as e:
        logger.error(f"❌ AI 审核异常终止: {e}")
        # 容错降级逻辑: 如果 AI 无法判定，退而求其次
        # Directly output all effective abnormals for repair if AI fails
        confirmed = effective_abnormal if 'effective_abnormal' in locals() else []
        logger.warning(f"⚠️ AI 降级：全量放行 {len(confirmed)} 只异常股票进入补采阶段。")
        output = {
            "confirmed_bad_codes": confirmed + (mandatory_bad if 'mandatory_bad' in locals() else []),
            "repair_mode": "repair" if confirmed else "skip",
            "repair_concurrency": 20 if confirmed else 0,
            "decision": "FALLBACK_TO_MANUAL"
        }
        print(f"GSD_OUTPUT_JSON: {json.dumps(output)}")
        sys.exit(0) # 保持 Workflow 继续

if __name__ == "__main__":
    asyncio.run(main())
