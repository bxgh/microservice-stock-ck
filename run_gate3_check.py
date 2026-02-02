
import asyncio
import os
import sys
import logging
import json

logging.basicConfig(level=logging.ERROR)

os.environ['CLICKHOUSE_HOST'] = '127.0.0.1'
os.environ['MYSQL_HOST'] = '127.0.0.1'
os.environ['MYSQL_PORT'] = '36301'
os.environ['REDIS_HOST'] = '127.0.0.1'

from core.post_market_gate_service import PostMarketGateService

async def main():
    service = PostMarketGateService()
    await service.initialize()
    
    date_str = '2026-01-29'
    print(f"Running Gate-3 check for {date_str}...")
    
    report = await service.run_gate_check(date_str)
    
    print('AUDIT_REPORT_JSON_START')
    print(json.dumps(report, indent=4))
    print('AUDIT_REPORT_JSON_END')
    
    await service.close()

if __name__ == '__main__':
    asyncio.run(main())
