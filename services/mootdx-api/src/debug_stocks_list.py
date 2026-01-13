
import asyncio
from handlers.mootdx_handler import MootdxHandler
import pandas as pd

async def main():
    handler = MootdxHandler(pool_size=1)
    await handler.initialize()
    
    try:
        # 获取深圳市场股票
        print("Fetching SZ stocks...")
        df_sz = await handler.get_stocks([], {"market": 0})
        print(f"SZ count: {len(df_sz)}")
        print("SZ head:\n", df_sz.head())
        
        # 看看 000005 是否在里面
        if not df_sz.empty:
            # 看看以 00 开头的代码
            sz_00 = df_sz[df_sz['code'].str.startswith('00')]
            print(f"\nSZ codes starting with '00' count: {len(sz_00)}")
            print("First 50:\n", sz_00['code'].tolist()[:50])
            
            # 过滤 A 股
            sz_a = df_sz[df_sz['code'].str.startswith(('000', '001', '002', '300', '301'))]
            print(f"SZ A-share count: {len(sz_a)}")
            
        # 获取上海市场股票
        print("\nFetching SH stocks...")
        df_sh = await handler.get_stocks([], {"market": 1})
        print(f"SH count: {len(df_sh)}")
        
        if not df_sh.empty:
            # 600xxx, 601xxx, 603xxx, 605xxx, 688xxx
            sh_a = df_sh[df_sh['code'].str.startswith(('600', '601', '603', '605', '688'))]
            print(f"SH A-share count: {len(sh_a)}")

    finally:
        await handler.close()

if __name__ == "__main__":
    asyncio.run(main())
