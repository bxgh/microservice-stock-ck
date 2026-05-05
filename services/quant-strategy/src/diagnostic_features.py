import asyncio
import pandas as pd
from src.orchestrator.orchestrator import StrategyOrchestrator
from src.orchestrator.data_loader import DataLoader
import logging

# 禁用冗余日志
logging.basicConfig(level=logging.ERROR)

async def diagnostic():
    target_code = "688802.SH"
    orchestrator = StrategyOrchestrator()
    loader = DataLoader()
    
    # 模拟最新一天的分析
    end_date = "2026-02-08"
    start_date = "2026-02-01"
    
    # 1. 选择对标
    selection = await orchestrator.peer_selector.select_peers(target_code)
    peers = selection.peers
    
    # 2. 加载数据
    data = await loader.load_strategy_data(target_code, peers, start_date, end_date)
    target_df = data['target']
    peers_df = data['peers']
    
    print("\n=== 核对每个指标的实际情况 (诊断报告) ===")
    print(f"目标股: {target_code} (沐曦股份)")
    print(f"分析日期: {end_date}")
    print(f"所属行业: {selection.target_ths_industry}")
    print(f"已选对标数量: {len(peers)}")
    print(f"有特征数据的对标数量: {peers_df['ts_code'].nunique() if not peers_df.empty else 0}")
    
    # 3. 提取目标股特征 (2026-02-08)
    if not target_df.empty:
        latest_target = target_df[target_df['trade_date'] == '2026-02-08']
        if latest_target.empty:
            latest_target = target_df.iloc[-1:]
            print(f"⚠️ 2026-02-08 无目标股数据，使用最近日期: {latest_target['trade_date'].iloc[0]}")
            
        target_vals = latest_target.iloc[0][[f'f{i}' for i in range(1, 10)]].to_dict()
    else:
        target_vals = {}
        print("❌ 错误: 目标股特征数据不存在")
        
    # 4. 提取对手特征 (2026-02-08)
    if not peers_df.empty:
        latest_peers = peers_df[peers_df['trade_date'] == (latest_target['trade_date'].iloc[0] if not latest_target.empty else '2026-02-08')]
        peer_data = latest_peers[['ts_code'] + [f'f{i}' for i in range(1, 10)]]
    else:
        peer_data = pd.DataFrame()
        print("⚠️ 警告: 同行对标在指定日期无特征数据")
        
    # 5. 输出详细表格
    print("\n--- 原始指标数值表 ---")
    
    # 构造展示表格
    display_rows = []
    if target_vals:
        row = {"Stock": f"TARGET: {target_code}"}
        row.update({k: f"{v:.2f}" for k, v in target_vals.items()})
        display_rows.append(row)
        
    if not peer_data.empty:
        for _, r in peer_data.iterrows():
            row = {"Stock": r['ts_code']}
            row.update({f'f{i}': f"{r[f'f{i}']:.2f}" for i in range(1, 10)})
            display_rows.append(row)
            
    if display_rows:
        df_show = pd.DataFrame(display_rows)
        print(df_show.to_string(index=False))
    else:
        print("无数据可供展示")

    # 6. 计算分位点并打印过程 (以 f1 为例)
    if target_vals and not peer_data.empty:
        f1_target = target_vals['f1']
        f1_peers = peer_data['f1'].values
        # (peer_vals <= target_val).mean() * 100
        smaller_count = (f1_peers <= f1_target).sum()
        total_count = len(f1_peers)
        percentile = (smaller_count / total_count) * 100
        print(f"\n--- 计算逻辑核对 (以 f1 为例) ---")
        print(f"目标 f1: {f1_target:.2f}")
        print(f"对手 f1 集合: {[f'{x:.2f}' for x in f1_peers]}")
        print(f"计算过程: (对手中小于等于目标值的数量 {smaller_count}) / (对手总数 {total_count}) * 100 = {percentile:.2f}%")

if __name__ == "__main__":
    asyncio.run(diagnostic())
