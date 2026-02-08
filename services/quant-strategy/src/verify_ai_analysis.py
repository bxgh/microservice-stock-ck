import asyncio
import logging
import os
from src.orchestrator.orchestrator import StrategyOrchestrator
from src.orchestrator.report_generator import ReportGenerator

# 配置日志
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("verify-ai-analysis")

async def main():
    target_code = "688802.SH"
    trade_date = "2026-02-05" 
    
    logger.info(f"🚀 启动 {target_code} AI 增强分析流程 (日期: {trade_date})...")
    
    try:
        # 1. 运行 Orchestrator
        orchestrator = StrategyOrchestrator()
        result = await orchestrator.run_analysis(
            target_code=target_code,
            current_date=trade_date
        )
        
        if "error" in result:
            logger.error(f"❌ 分析失败: {result['error']}")
            return

        # 2. 生成报告
        report_md = ReportGenerator.generate_markdown(result)
        
        # 3. 保存并打印报告
        output_file = "ai_analysis_report_688802.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_md)
            
        print("\n" + "="*60)
        print("AI 增强分析报告生成成功!")
        print(f"报告已保存至: {output_file}")
        print("="*60)
        
        # 打印 AI 核心总结部分
        if result['analysis'].get('ai_insight'):
            insight = result['analysis']['ai_insight']
            print(f"\n[AI 核心综述]:\n{insight['summary']}")
            print(f"\n[智能建议]:\n动作: {insight['advice']['action']}\n原因: {insight['advice']['reason']}")
        else:
            print("\n⚠️ 警告: 未能生成 AI 解读内容，请检查 API 配置或网络。")
        print("="*60 + "\n")
            
    except Exception as e:
        logger.error(f"❌ 运行出错: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
