
import asyncio
import os
import sys
import logging

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), 'services/gsd-worker/src'))
sys.path.append(os.path.join(os.getcwd(), 'libs/gsd-shared'))

# Env setup
os.environ['CLICKHOUSE_HOST'] = '127.0.0.1'
os.environ['MYSQL_HOST'] = '127.0.0.1'
os.environ['MYSQL_PORT'] = '36301'
os.environ['REDIS_HOST'] = '127.0.0.1'

from jobs.audit_tick_resilience import AuditJob

def normalize_code(code):
    if '.' in code:
        return code.split('.')[0] if len(code.split('.')[0]) == 6 else code.split('.')[-1]
    return code

async def main():
    logging.basicConfig(level=logging.ERROR)
    
    print("Initializing AuditJob for 2026-01-30...")
    job = AuditJob()
    job.target_date = "2026-01-30"
    await job.initialize()
    
    try:
        # 1. Get scope & Run Validation
        target_scope = await job.get_target_scope()
        missing_list, invalid_list = await job.execute_validation(target_scope)
        
        failed_codes = list(set(missing_list + [i['code'] for i in invalid_list]))
        print(f"\nFound {len(failed_codes)} abnormal stocks.")
        
        if not failed_codes:
            return

        # 2. Fetch ALL K-Line data for the day
        ds = job.target_date.replace('-', '')
        kline_map = {}
        async with job.service.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"""
                    SELECT stock_code, volume, amount, close_price, open_price, high_price, low_price
                    FROM stock_data.stock_kline_daily
                    WHERE trade_date = '{ds}'
                """)
                rows = await cursor.fetchall()
                for r in rows:
                    std = normalize_code(r[0])
                    kline_map[std] = {
                        'full_code': r[0],
                        'vol': r[1],
                        'amt': r[2],
                        'close': r[3],
                        'open': r[4],
                        'high': r[5],
                        'low': r[6]
                    }

        print("\n" + "="*110)
        print(f"{'Code':<8} | {'Status':<8} | {'Full Code':<10} | {'K-Vol':<10} | {'K-Close':<8} | {'K-Open':<8} | {'Diagnosis'}")
        print("-" * 110)

        # Diagnose Missing
        for code in missing_list:
            k = kline_map.get(code)
            diag = "UNKNOWN"
            k_vol = "N/A"
            k_full = "N/A"
            k_close = "N/A"
            k_open = "N/A"
            
            if k:
                k_vol = k['vol']
                k_full = k['full_code']
                k_close = k['close']
                k_open = k['open']
                if k['vol'] == 0:
                    diag = "🟡 SUSPENDED (Vol=0)"
                elif k['open'] <= 0 or k['close'] <= 0:
                    diag = "🟡 SUSPENDED (Price=0)"
                else:
                    diag = "🔴 REAL MISSING (Has Vol)"
            else:
                diag = "❓ NO K-LINE RECORD (Why in target scope?)"
            
            print(f"{code:<8} | {'MISSING':<8} | {k_full:<10} | {str(k_vol):<10} | {str(k_close):<8} | {str(k_open):<8} | {diag}")

        # Diagnose Invalid
        for item in invalid_list:
            code = item['code']
            k = kline_map.get(code)
            k_vol = k['vol'] if k else "N/A"
            k_full = k['full_code'] if k else "N/A"
            k_close = k['close'] if k else "N/A"
            k_open = k['open'] if k else "N/A"
            
            print(f"{code:<8} | {'INVALID':<8} | {k_full:<10} | {str(k_vol):<10} | {str(k_close):<8} | {str(k_open):<8} | {'🔴 DATA MISMATCH: ' + item['reason'][:30]}")

    finally:
        await job.close()

if __name__ == '__main__':
    asyncio.run(main())
