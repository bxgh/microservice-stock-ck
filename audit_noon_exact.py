#!/usr/bin/env python3
"""
午盘分笔数据高精度审计脚本 (2026-02-02)
基于 ClickHouse 内部快照表 snapshot_data_distributed 进行成交量一致性对账。
"""

from clickhouse_driver import Client
import json

# 配置
CH_CONFIG = {
    'host': '192.168.151.41',
    'user': 'admin',
    'password': 'admin123',
    'database': 'stock_data'
}

TARGET_DATE = '2026-02-02'
NOON_ANCHOR = f'{TARGET_DATE} 11:30:00'
NOON_END = f'{TARGET_DATE} 11:30:05'

def run_audit():
    client = Client(**CH_CONFIG)
    
    print(f"🚀 开始早盘数据对账 (锚点: {NOON_ANCHOR})")
    
    # 1. 获取全市场 11:30 左右的快照总量
    print("   -> 提取 11:30 静态快照真值...")
    # 使用 argMax 确保拿到每只股票最接近 11:30 的那一笔
    snap_sql = f"""
        SELECT 
            stock_code, 
            argMax(total_volume, snapshot_time) as snap_vol
        FROM snapshot_data_distributed 
        WHERE trade_date = '{TARGET_DATE}'
          AND snapshot_time >= '{TARGET_DATE} 11:29:00'
          AND snapshot_time <= '{NOON_END}'
        GROUP BY stock_code
    """
    snap_rows = client.execute(snap_sql)
    snap_map = {r[0]: r[1] for r in snap_rows}
    print(f"   ✓ 获取到 {len(snap_map)} 只股票的快照基准")

    if not snap_map:
        print("❌ 错误：快照表中没有今日早盘数据！")
        return

    # 2. 统计分笔表中的早盘总量
    print("   -> 聚合 ClickHouse 分笔成交量 (tick_time <= 11:30:00)...")
    tick_sql = f"""
        SELECT 
            stock_code, 
            sum(volume) as tick_sum
        FROM tick_data_intraday
        WHERE trade_date = '{TARGET_DATE}'
          AND tick_time <= '11:30:00'
        GROUP BY stock_code
    """
    tick_rows = client.execute(tick_sql)
    tick_map = {r[0]: r[1] for r in tick_rows}

    # 3. 对比分析
    results = []
    total_checked = 0
    bad_count = 0
    
    print("\n--- 差异审计报告 (误差 > 1%) ---")
    print(f"{'Code':<10} | {'SnapVol':<12} | {'TickSum':<12} | {'Diff%':<8}")
    print("-" * 50)

    # 遍历所有有快照的股票
    for code, s_vol_lots in snap_map.items():
        if s_vol_lots == 0:
            continue
        
        # 换算单位：快照为手(lots)，分笔为股(shares)
        s_vol = s_vol_lots * 100
        t_sum = tick_map.get(code, 0)
        total_checked += 1
        
        # 计算误差
        diff = t_sum - s_vol
        diff_pct = abs(diff) / s_vol if s_vol > 0 else 0
        
        if diff_pct > 0.01: # 1% 阈值
            bad_count += 1
            status = "MISSING" if diff < 0 else "EXCESSIVE"
            results.append({
                "code": code,
                "snap_vol": s_vol,
                "tick_sum": t_sum,
                "diff_pct": round(diff_pct * 100, 2),
                "type": status
            })
            if bad_count <= 40: # 打印前 40 条
                marker = "▼" if diff < 0 else "▲"
                print(f"{code:<10} | {s_vol:<12,d} | {t_sum:<12,d} | {diff_pct:>7.2%} {marker} {status}")

    print("-" * 50)
    print(f"统计：已核查 {total_checked} 只股票，发现 {bad_count} 只涉及早盘数据缺口。")
    
    # 导出
    with open('noon_bad_stocks.json', 'w') as f:
        json.dump(results, f, indent=4)
    print("\n✅ 详细清单已导出至: noon_bad_stocks.json")

if __name__ == "__main__":
    run_audit()
