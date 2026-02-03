import sys
import asyncio
import aiohttp
import os
import json
# gsd-worker environment setup
sys.path.append("/app/src")
sys.path.append("/app/libs/gsd-shared")

from core.clickhouse_client import ClickHouseClient

STOCKS = ["600208", "603269", "002481", "600123", "000531", "601566", "002664", "601186", "300508", "000728", "603008", "000016", "000650", "002484", "600611", "002603", "600039", "601001", "600955", "600664", "002958", "603628", "002572", "002488", "002448", "002400", "002289", "002492", "000889", "002171", "600495", "002097", "300168", "002372", "600975", "600886", "002482", "002983", "600153", "002173", "600255", "603458", "600345", "600335", "300190", "000017", "002379", "603229", "000692", "001267", "601990", "600241", "600929", "600109", "603978", "002383", "002445", "600498", "002388", "000952", "000610", "601800", "603659", "601311", "600036", "000679", "601928", "002759", "603011", "000801", "000811", "002454", "000813", "600177", "002104", "000429", "300290", "002602", "600120", "002500", "000937", "300416", "600780", "600754", "600489", "002146", "601236", "600256", "300150", "002452", "002501", "600375", "002966", "600552", "002141", "601238", "600155", "002939", "300635", "002123", "601212", "600326", "002419", "603429", "600606", "600521", "002303", "000603", "601228", "002547", "600493", "000517", "300256", "600734", "300603", "600617", "002252", "003039", "002678", "300759", "002175", "600406", "000756", "600250", "605366", "600110", "603012", "002072", "603889", "603259", "600173", "601515", "600491", "002226", "600239", "300404", "001286", "601788", "300790", "600025", "301215", "300377", "600127", "600236", "600906", "000158", "002611", "002073", "600150", "601188", "600252", "688425", "002009"]

async def main():
    print(f"Checking {len(STOCKS)} stocks...")
    
    # 1. Fetch Tick Aggregates (ClickHouse)
    print("Fetching Tick Data from ClickHouse...")
    try:
        ch = ClickHouseClient()
        await ch.connect()
        
        placeholders = ",".join([f"'{c}'" for c in STOCKS])
        
        sql = f"""
            SELECT stock_code, sum(volume) as tick_vol, argMax(price, tick_time) as close
            FROM tick_data_intraday
            WHERE trade_date = '2026-02-03' AND stock_code IN ({placeholders})
            GROUP BY stock_code
        """
        
        rows = ch.execute(sql)
        tick_map = {r[0]: {'vol': float(r[1]), 'close': float(r[2])} for r in rows}
        print(f"Loaded {len(tick_map)} stocks from ClickHouse.")
        ch.disconnect()
    except Exception as e:
        print(f"ClickHouse Error: {e}")
        return

    # 2. Fetch Snapshots (Mootdx API)
    print("Fetching Snapshots from Mootdx API...")
    snap_map = {}
    async with aiohttp.ClientSession() as session:
        batch_size = 50
        for i in range(0, len(STOCKS), batch_size):
            batch = STOCKS[i:i+batch_size]
            codes_str = ",".join(batch)
            url = f"http://127.0.0.1:8003/api/v1/quotes?codes={codes_str}"
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data:
                            code = item['code']
                            # Volume is in lots
                            vol = float(item['vol']) * 100
                            snap_map[code] = {'vol': vol, 'close': float(item['price'])}
                    else:
                        print(f"Error fetching batch {i}: {resp.status}")
            except Exception as e:
                print(f"Exception fetching batch {i}: {e}")
                
    print(f"Loaded {len(snap_map)} snapshots.")

    # 3. Compare
    print("\n" + "="*80)
    print(f"{'Code':<10} {'Tick Vol':<15} {'Snap Vol':<15} {'Diff':<12} {'Diff %':<10} {'Status'}")
    print("-" * 80)
    
    valid_count = 0
    missing_count = 0
    bad_count = 0
    
    STOCKS.sort()
    
    for code in STOCKS:
        tick_info = tick_map.get(code)
        snap_info = snap_map.get(code)
        
        if not tick_info:
            print(f"{code:<10} {'MISSING':<15} {int(snap_info['vol']) if snap_info else '-':<15} {'-':<12} {'-':<10} 🔴 No Tick")
            missing_count += 1
            continue
            
        if not snap_info:
            print(f"{code:<10} {int(tick_info['vol']):<15} {'MISSING':<15} {'-':<12} {'-':<10} ⚠️ No Snap")
            continue
            
        t_vol = tick_info['vol']
        s_vol = snap_info['vol']
        
        diff = t_vol - s_vol
        abs_diff = abs(diff)
        pct = abs_diff / s_vol if s_vol > 0 else 0
        
        status = "✅ OK"
        # Logic: 2% diff
        if pct > 0.02 and abs_diff > 100000:
             status = "❌ FAIL"
             bad_count += 1
        elif pct > 0.02:
             status = "⚠️ WARN" # Small volume mismatch
             valid_count += 1
        else:
             valid_count += 1
             
        if pct > 0.005 or status != "✅ OK": 
            print(f"{code:<10} {int(t_vol):<15} {int(s_vol):<15} {int(diff):<12} {pct:.2%}      {status}")
            
    print("-" * 80)
    print(f"Summary: Total {len(STOCKS)} | Valid {valid_count} | Bad {bad_count} | Missing Tick {missing_count}")

if __name__ == "__main__":
    asyncio.run(main())
