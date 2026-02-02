
import asyncio
import aiohttp
import random
import time
from clickhouse_driver import Client

# ----------------- 配置 -----------------
CH_HOST = '192.168.151.41'
CH_PORT = 9000
CH_USER = 'admin'
CH_PASS = 'admin123'
CH_DB = 'stock_data'

MOOTDX_API = 'http://127.0.0.1:8003/api/v1'
AUDIT_DATE = '2026-02-02'
SAMPLE_SIZE = 30 # 稍微减小样本量以保证 FINAL 查询速度
# ----------------------------------------

def get_ch_client():
    return Client(host=CH_HOST, port=CH_PORT, user=CH_USER, password=CH_PASS, database=CH_DB)

async def fetch_snapshot(session, codes):
    url = f"{MOOTDX_API}/quotes"
    codes_str = ",".join(codes)
    try:
        async with session.get(url, params={"codes": codes_str}, timeout=10) as resp:
            if resp.status == 200:
                return await resp.json()
    except Exception as e:
        print(f"Fetch failed: {e}")
    return []

async def main():
    print(f"🕵️ Starting Intraday Tick Accuracy Audit (Precise Version) for {AUDIT_DATE}...")
    client = get_ch_client()
    
    # 1. 获取今日有数据的股票列表
    print("Step 1: Fetching stock list...")
    stocks_raw = client.execute(f"SELECT DISTINCT stock_code FROM tick_data_intraday WHERE trade_date = '{AUDIT_DATE}'")
    all_stocks = [r[0] for r in stocks_raw]
    
    if not all_stocks:
        print("❌ No data found in ClickHouse for today!")
        return

    # 2. 随机抽样
    sample_stocks = random.sample(all_stocks, min(SAMPLE_SIZE, len(all_stocks)))
    print(f"Step 2: Sampled {len(sample_stocks)} stocks.")
    
    # 3. 获取快照数据
    print("Step 3: Fetching snapshots...")
    prefixed_codes = []
    for code in sample_stocks:
        if code.startswith(('6', '9')): prefixed_codes.append(f"sh{code}")
        else: prefixed_codes.append(f"sz{code}")
        
    async with aiohttp.ClientSession() as session:
        snapshots = await fetch_snapshot(session, prefixed_codes)
    
    snapshot_map = {s['code']: s for s in snapshots}
    
    # 4. 逐一对比
    print("Step 4: Reconciling data records (using FINAL to deduplicate)...")
    results = []
    
    for code in sample_stocks:
        snap = snapshot_map.get(code)
        if not snap or snap.get('vol', 0) == 0:
            continue
            
        # 使用 FINAL 确保查询到的是去重后的结果
        # 注意: tick_data_intraday 是分布式表，对它用 FINAL 会下发到所有本地表
        ch_data = client.execute(f"""
            SELECT sum(volume), sum(amount) 
            FROM tick_data_intraday FINAL
            WHERE stock_code = '{code}' AND trade_date = '{AUDIT_DATE}'
        """)[0]
        
        ch_vol = int(ch_data[0] or 0)
        ch_amt = float(ch_data[1] or 0.0)
        
        # 转换逻辑: A股成交量快照通常为“手”，ClickHouse 存储为“股”
        # 部分特定证券(如可转债)可能不同，但对 A股 抽样基本适用 * 100
        snap_vol_lots = int(snap.get('vol', 0))
        snap_vol_shares = snap_vol_lots * 100
        snap_amt = float(snap.get('amount', 0.0))
        
        # 特别处理: 如果 snap_vol_shares 与 ch_vol 差了接近 100 倍，说明 snap 已经是股了
        # (mootdx 的某些服务器或不同版本返回单位不同)
        if abs(ch_vol - snap_vol_lots) < abs(ch_vol - snap_vol_shares):
             snap_vol_shares = snap_vol_lots

        # 计算误差 (%)
        vol_err = (abs(ch_vol - snap_vol_shares) / snap_vol_shares * 100) if snap_vol_shares > 0 else 0
        amt_err = (abs(ch_amt - snap_amt) / snap_amt * 100) if snap_amt > 0 else 0
        
        results.append({
            "code": code,
            "ch_vol": ch_vol,
            "snap_vol": snap_vol_shares,
            "vol_err": vol_err,
            "ch_amt": ch_amt,
            "snap_amt": snap_amt,
            "amt_err": amt_err
        })

    # 5. 输出报告
    if not results:
        print("❌ No valid matching data found.")
        return
        
    total_vol_err = sum(r['vol_err'] for r in results)
    total_amt_err = sum(r['amt_err'] for r in results)
    avg_vol_err = total_vol_err / len(results)
    avg_amt_err = total_amt_err / len(results)
    
    print("\n" + "="*60)
    print(f"📊 ACCURACY AUDIT REPORT (PRECISE)")
    print(f"Date: {AUDIT_DATE} | Time: {time.strftime('%H:%M:%S')}")
    print("="*60)
    print(f"Sample Size:   {len(results)} stocks")
    print(f"Avg Vol Error: {avg_vol_err:.4f}%")
    print(f"Avg Amt Error: {avg_amt_err:.4f}%")
    print("-" * 60)
    
    # 排序查看误差最大的个股
    results.sort(key=lambda x: x['vol_err'], reverse=True)
    print(f"{'Code':<10} {'CH Vol (股)':<12} {'Snap Vol (股)':<12} {'Error':<10}")
    for r in results[:10]: # 显示前10个
        status = "🚨" if r['vol_err'] > 1.0 else "✅"
        print(f"{status} {r['code']:<8} {r['ch_vol']:<12} {r['snap_vol']:<12} {r['vol_err']:.4f}%")
    
    print("="*60)
    print("Audit Result Note:")
    print("- Errors < 1% are generally due to sync latency between collector and snapshot API.")
    print("- Vol Errors: Uses 100x heuristic if needed.")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
