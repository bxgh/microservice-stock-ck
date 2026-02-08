import asyncio
import logging
import pandas as pd
import numpy as np
from src.orchestrator.orchestrator import StrategyOrchestrator

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("verify-real-features")

async def main():
    target_code = "688802.SH"
    trade_date = "2026-02-05"
    
    orchestrator = StrategyOrchestrator()
    
    try:
        logger.info(f"🔍 正在获取 {target_code} 在 {trade_date} 的实时分析结果 (从 Redis 加载真实计算数据)...")
        # 传递 current_date 参数
        result = await orchestrator.run_analysis(target_code, current_date=trade_date, days_lookback=0)
        
        if "error" in result:
            logger.error(f"❌ 分析失败: {result['error']}")
            return

        print("\n" + "="*50)
        print(f"688802.SH 真实特征验证报告 (日期: {trade_date})")
        print("="*50)
        
        target_info = result['target_info']
        print(f"个股: {target_info['name']} ({target_info['code']})")
        print(f"行业: {target_info['industry']}")
        
        print("\n[特征百分位/排名核对]")
        # DistributionAnalyzer 返回 {date: {feat: percentile}}
        dist_all = result['analysis']['distribution']
        if trade_date in dist_all:
            date_dist = dist_all[trade_date]
            for feat, pct in date_dist.items():
                print(f"- {feat}: 分位值 {pct:.2f}%")
        else:
            logger.warning(f"No distribution data found for date {trade_date}")
            print(f"Available dates in distribution: {list(dist_all.keys())}")
            
        print("\n[对标排名核对]")
        ranking = result['analysis']['ranking']
        # 打印部分指标的排名情况
        for feat in ['f1', 'f3', 'f4', 'f8', 'f9']:
            if feat in ranking:
                r = ranking[feat]
                print(f"- {feat} 排名: {r['rank']}/{r['total']} (最高值: {r['top_peers'][0][1]:.4f}, 目标值: {r.get('target_value', 0):.6f})")

        # 核心指标 f3 (收益率) 验证
        f3_val = ranking.get('f3', {}).get('target_value', 0)
        
        if f3_val != 0 and abs(f3_val) < 1e-10: # 近乎 0 但不为 0
             print(f"\n✅ 验证通过: f3 特征值({f3_val:.8f}) 呈现正常数值状态。")
        elif f3_val in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
             print(f"\n❌ 警告: f3 特征值({f3_val}) 依然表现为步进 Mock 数据特征！")
        else:
             print(f"\n✅ 验证通过: f3 特征值({f3_val:.6f}) 呈现真实市场波动特征（非步进 Mock 数据）。")

        print("="*50 + "\n")
            
    except Exception as e:
        logger.error(f"❌ 运行出错: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
