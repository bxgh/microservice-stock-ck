import asyncio
import akshare as ak
import pandas as pd
import aiomysql
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MarginSummaryCollector:
    def __init__(self, mysql_config):
        self.mysql_config = mysql_config

    async def collect(self):
        logger.info("Fetching Macro Margin Summary from AkShare (SH + SZ)...")
        try:
            # 1. 采集沪深两市宏观汇总数据 (包含历史)
            df_sh = ak.macro_china_market_margin_sh()
            df_sz = ak.macro_china_market_margin_sz()
            
            # 2. 对齐与合并
            # SH: ['日期', '融资买入额', '融资余额', ...]
            # SZ: ['日期', '融资买入额', '融资余额', ...]
            
            df_sh_clean = df_sh[['日期', '融资买入额', '融资余额']].copy()
            df_sh_clean.columns = ['trade_date', 'buy_sh', 'bal_sh']
            
            df_sz_clean = df_sz[['日期', '融资买入额', '融资余额']].copy()
            df_sz_clean.columns = ['trade_date', 'buy_sz', 'bal_sz']

            # 强制转换为日期格式
            df_sh_clean['trade_date'] = pd.to_datetime(df_sh_clean['trade_date']).dt.date
            df_sz_clean['trade_date'] = pd.to_datetime(df_sz_clean['trade_date']).dt.date

            # 合并
            df_total = pd.merge(df_sh_clean, df_sz_clean, on='trade_date', how='outer').fillna(0)
            df_total['margin_buy'] = df_total['buy_sh'] + df_total['buy_sz']
            df_total['margin_balance'] = df_total['bal_sh'] + df_total['bal_sz']
            
            # 过滤 2024 以后的数据以减少落库压力 (指标窗口需要前置数据)
            df_total = df_total[df_total['trade_date'] >= datetime.strptime('2023-11-01', '%Y-%m-%d').date()]
            
            # 3. 落库
            await self._save_to_mysql(df_total[['trade_date', 'margin_buy', 'margin_balance']])
            
        except Exception as e:
            logger.error(f"Error collecting margin summary: {e}")
            raise

    async def _save_to_mysql(self, df):
        conn = await aiomysql.connect(**self.mysql_config, autocommit=True)
        async with conn.cursor() as cursor:
            sql = """
            INSERT INTO market_margin_summary (trade_date, margin_buy, margin_balance)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
            margin_buy=VALUES(margin_buy),
            margin_balance=VALUES(margin_balance)
            """
            data = [
                (row['trade_date'], float(row['margin_buy']), float(row['margin_balance']))
                for _, row in df.iterrows()
            ]
            await cursor.executemany(sql, data)
            logger.info(f"Successfully upserted {len(data)} margin summary records.")
        conn.close()

async def main():
    logging.basicConfig(level=logging.INFO)
    mysql_config = {
        'host': '127.0.0.1', 
        'port': 36301, 
        'user': 'root', 
        'password': 'alwaysup@888', 
        'db': 'alwaysup'
    }
    collector = MarginSummaryCollector(mysql_config)
    await collector.collect()

if __name__ == "__main__":
    asyncio.run(main())
