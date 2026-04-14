"""
每日流动性复盘任务 - 整合版 (VOL-01 & VOL-02)
"""
import asyncio
import logging
import os
import pandas as pd
from datetime import datetime
from analyzers.liquidity_analyzer import LiquidityMomentumAnalyzer
from data_access.liquidity_dao import LiquidityDAO
from data_access.mysql_pool import MySQLPoolManager
from data_access.clickhouse_pool import ClickHousePoolManager

logger = logging.getLogger(__name__)

class ReviewLiquidityJob:
    """流动性复盘核心作业类"""
    
    def __init__(self, mootdx_api_url: str = None):
        if not mootdx_api_url:
            mootdx_api_url = os.getenv("MOOTDX_API_URL", "http://127.0.0.1:8003")
        self.analyzer = LiquidityMomentumAnalyzer(mootdx_api_url=mootdx_api_url)
        self.dao = LiquidityDAO()

    async def run(self, backfill_days: int = 300):
        """执行流动性分析与状态记录"""
        logger.info(f"Starting Liquidity Review Job (backfill_days={backfill_days})...")
        
        try:
            # 1. 从 MySQL 加载两地宽基指数全量数据 (Tushare 数据源)
            sh_df = await self._fetch_index_klines("000001.SH")
            sz_df = await self._fetch_index_klines("399106.SZ")
            
            # 1.5 预计算指数收益率
            if not sh_df.empty:
                sh_df['pct_chg'] = sh_df['close'].pct_change() * 100
            
            # 执行 VOL-01 指数分析 (获取基础时间轴)
            df_vol_01_all = await self.analyzer.analyze_vol01(sh_df, sz_df)
            if df_vol_01_all is None or df_vol_01_all.empty:
                logger.error("Failed to process VOL-01 index data.")
                return

            # 获取回填所需的交易日列表
            all_trading_dates = df_vol_01_all['datetime'].dt.strftime('%Y-%m-%d').tolist()
            # 确保有足够的前置窗口 (60天) 用于 Z-Score 计算，所以从 backfill_days + 60 开始处理
            start_idx = max(0, len(all_trading_dates) - backfill_days - 60)
            target_dates = all_trading_dates[start_idx:]
            
            logger.info(f"Processing {len(target_dates)} days from {target_dates[0]} to {target_dates[-1]}")

            # 2. 加载静态或全量辅助数据
            df_margin = await self._fetch_margin_history()
            df_industry = await self._fetch_industry_map()
            
            # VOL-02 的基础 (融资买入占比) 可以在向量化层面先做一部分
            df_vol_01_02 = self.analyzer.analyze_vol02(df_vol_01_all.copy(), df_margin)
            
            # 3. 逐日处理数据拉取与基础特征计算
            vol03_raw = [] # ratio_c
            vol04_raw = [] # count_frozen
            
            # 用于方案 A 的市值缓存: {code: last_known_circ_mv}
            mv_cache = {}
            
            logger.info("Starting daily data acquisition loop...")
            for i, t_date in enumerate(target_dates):
                if i % 100 == 0:
                    logger.info(f"Progress: Fetching data for {t_date} ({i}/{len(target_dates)})")
                
                # A. 获取当日个股 K 线
                df_klines = await self._fetch_stock_klines_by_date(t_date)
                
                # B. 获取当日市值快照并更新缓存
                df_basic = await self._fetch_daily_basic_by_date(t_date)
                # 更新缓存 (将当日新数据合并进全量缓存)
                if not df_basic.empty:
                    current_day_mv = dict(zip(df_basic['code'], df_basic['circ_mv']))
                    mv_cache.update(current_day_mv)
                
                # C. 应用 A 方案: 使用缓存构造当日完整的市值视图
                # 仅针对当日在 K 线中出现的股票
                if not df_klines.empty:
                    # 构造当日 MV DataFrame
                    codes_in_kline = df_klines['code'].tolist()
                    daily_mv_list = [{"code": c, "circ_mv": mv_cache.get(c)} for c in codes_in_kline if c in mv_cache]
                    df_mv_snapshot = pd.DataFrame(daily_mv_list)
                    
                    # D. 调用分析器核心逻辑
                    v03 = self.analyzer.analyze_vol03(df_klines, df_industry)
                    v04 = self.analyzer.analyze_vol04(df_klines, df_mv_snapshot)
                    
                    vol03_raw.append(v03['ratio_c'])
                    vol04_raw.append(v04['count_frozen'])
                else:
                    vol03_raw.append(0.0)
                    vol04_raw.append(0)

            # 4. 获取 VOL-05 & VOL-06 所需的序列数据 (ClickHouse)
            logger.info("Fetching Repo and ETF series data from ClickHouse...")
            df_repo_all = await self._fetch_repo_rates()
            df_etf_all = await self._fetch_etf_volume_series("510300.SH")
            
            # 5. 时间序列计算 (Z-Score & Regression)
            logger.info("Calculating time-series metrics...")
            s_vol03 = pd.Series(vol03_raw, index=target_dates)
            s_vol04 = pd.Series(vol04_raw, index=target_dates)
            
            # VOL-03: 3日平滑后 60日 Z-Score
            z_vol03 = self.analyzer.compute_zscore(s_vol03.rolling(3).mean(), window=60)
            
            # VOL-04: ΔCount -> Winsorize -> 60日 Z-Score
            z_vol04 = self.analyzer.compute_zscore(self.analyzer.winsorize(s_vol04.diff()), window=60)
            
            # 6. 持久化 (仅回写用户要求的 backfill_days 范围)
            final_start_idx = len(target_dates) - backfill_days
            if final_start_idx < 0: final_start_idx = 0
            
            dates_to_save = target_dates[final_start_idx:]
            logger.info(f"Final upsert for {len(dates_to_save)} days...")
            
            for i, t_date in enumerate(dates_to_save):
                if i % 100 == 0:
                    logger.info(f"Upserting progress: {i}/{len(dates_to_save)} ({t_date})")
                
                # 获取 VOL-01/02
                history_df = df_vol_01_02[df_vol_01_02['datetime'].dt.strftime('%Y-%m-%d') <= t_date]
                if history_df.empty: continue
                
                results = self.analyzer.identify_states(history_df, history_df)
                
                # 注入 03/04
                results['congestion_velocity'] = float(z_vol03.get(t_date, 0.0)) if not pd.isna(z_vol03.get(t_date)) else 0.0
                results['zombie_stock_derivation'] = float(z_vol04.get(t_date, 0.0)) if not pd.isna(z_vol04.get(t_date)) else 0.0
                
                # 注入 05 (Repo Rates)
                repo_slice = df_repo_all[df_repo_all['trade_date'] <= t_date]
                v05 = self.analyzer.analyze_vol05(repo_slice)
                results['cost_pulse_fdr007'] = v05['pulse_fdr007']
                results['non_bank_premium'] = v05['spread']
                
                # 注入 06 (ETF Depletion)
                t_dt = pd.to_datetime(t_date)
                etf_slice = df_etf_all[df_etf_all['datetime'] <= t_dt]
                index_slice = sh_df[sh_df['datetime'] <= t_dt]
                
                v06 = self.analyzer.analyze_vol06(etf_slice, index_slice)
                results['etf_depletion_rate'] = v06['depletion_slope']
                
                await self.dao.upsert_liquidity_record(results)

            logger.info(f"✓ Liquidity Review Job Finished. Integrated Count: {len(dates_to_save)}")
            
        except Exception as e:
            logger.error(f"Failed in ReviewLiquidityJob: {e}", exc_info=True)
            raise

    async def _fetch_margin_history(self) -> pd.DataFrame:
        """从 MySQL 加载历史融资汇总数据"""
        pool = await MySQLPoolManager.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT trade_date, margin_buy, margin_balance FROM market_margin_summary ORDER BY trade_date ASC")
                rows = await cursor.fetchall()
                if not rows:
                    return pd.DataFrame(columns=['trade_date', 'margin_buy', 'margin_balance'])
                df = pd.DataFrame(rows, columns=['trade_date', 'margin_buy', 'margin_balance'])
                # 类型转换
                df['margin_buy'] = df['margin_buy'].astype(float)
                df['margin_balance'] = df['margin_balance'].astype(float)
                return df

    async def _fetch_industry_map(self) -> pd.DataFrame:
        """获取行业标签映射 (申万一级)"""
        pool = await MySQLPoolManager.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT code, l1_name FROM stock_industry_sw")
                rows = await cursor.fetchall()
                return pd.DataFrame(rows, columns=['code', 'l1_name'])

    async def _fetch_all_stock_klines(self, start_date: str, end_date: str) -> pd.DataFrame:
        # 已废弃，改用 _fetch_stock_klines_by_date 以支持海量数据
        return pd.DataFrame()

    async def _fetch_index_klines(self, code: str) -> pd.DataFrame:
        """从 MySQL 加载指定指数的历史 K 线 (包含 close 价格以计算收益率)"""
        pool = await MySQLPoolManager.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = "SELECT trade_date as datetime, close, amount FROM stock_kline_daily WHERE code = %s ORDER BY trade_date ASC"
                await cursor.execute(query, (code,))
                rows = await cursor.fetchall()
                if not rows:
                    return pd.DataFrame(columns=['datetime', 'close', 'amount'])
                df = pd.DataFrame(rows, columns=['datetime', 'close', 'amount'])
                df['datetime'] = pd.to_datetime(df['datetime'])
                df['close'] = df['close'].astype(float)
                df['amount'] = df['amount'].astype(float)
                return df

    async def _fetch_stock_klines_by_date(self, trade_date: str) -> pd.DataFrame:
        """获取单日个股K线 (已过滤指数和新股，剔除ST)"""
        pool = await MySQLPoolManager.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = """
                SELECT k.code, k.amount, k.turnover
                FROM stock_kline_daily k
                INNER JOIN stock_basic_info b ON k.code = b.ts_code
                WHERE k.trade_date = %s
                  AND DATEDIFF(k.trade_date, b.list_date) >= 60
                  AND b.name NOT LIKE '%%ST%%'
                """
                await cursor.execute(query, (trade_date,))
                rows = await cursor.fetchall()
                df = pd.DataFrame(rows, columns=['code', 'amount', 'turnover'])
                # 转换 Decimal 为 float 以避免 pandas 运算错误
                df['amount'] = df['amount'].astype(float) if not df.empty else df['amount']
                df['turnover'] = df['turnover'].astype(float) if not df.empty else df['turnover']
                return df

    async def _fetch_all_daily_basic(self, start_date: str, end_date: str) -> pd.DataFrame:
        # 已废弃，改用 _fetch_daily_basic_by_date
        return pd.DataFrame()

    async def _fetch_daily_basic_by_date(self, trade_date: str) -> pd.DataFrame:
        """获取单日市值数据"""
        pool = await MySQLPoolManager.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = "SELECT ts_code as code, circ_mv FROM daily_basic WHERE trade_date = %s"
                await cursor.execute(query, (trade_date,))
                rows = await cursor.fetchall()
                df = pd.DataFrame(rows, columns=['code', 'circ_mv'])
                # 转换 Decimal 为 float
                df['circ_mv'] = df['circ_mv'].astype(float) if not df.empty else df['circ_mv']
                return df

    async def _fetch_repo_rates(self) -> pd.DataFrame:
        """从 ClickHouse 加载回购利率数据"""
        pool = await ClickHousePoolManager.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                query = "SELECT toDate(trade_date) as trade_date, repo_code, close_rate as close FROM stock_repo_rates_local ORDER BY trade_date ASC"
                await cursor.execute(query)
                rows = await cursor.fetchall()
                if not rows:
                    return pd.DataFrame(columns=['trade_date', 'repo_code', 'close'])
                df = pd.DataFrame(rows, columns=['trade_date', 'repo_code', 'close'])
                # trade_date 转为 yyyy-mm-dd 字符串方便后续过滤
                df['trade_date'] = df['trade_date'].astype(str)
                df['close'] = df['close'].astype(float)
                return df

    async def _fetch_etf_volume_series(self, code: str) -> pd.DataFrame:
        """从 ClickHouse 加载 ETF 日线成交量数据"""
        pool = await ClickHousePoolManager.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 注意: 这里的 510300 数据可能存在于日线表或从 tick 聚合
                # 优先查日线表 stock_kline_daily_local (CK)
                query = "SELECT toDate(trade_date) as datetime, volume FROM stock_kline_daily_local WHERE stock_code = %(code)s ORDER BY trade_date ASC"
                await cursor.execute(query, {"code": code})
                rows = await cursor.fetchall()
                if not rows:
                    return pd.DataFrame(columns=['datetime', 'volume'])
                df = pd.DataFrame(rows, columns=['datetime', 'volume'])
                df['datetime'] = pd.to_datetime(df['datetime'])
                df['volume'] = df['volume'].astype(float)
                return df

async def run_liquidity_review_task():
    """供调度器调用的静态入口"""
    job = ReviewLiquidityJob()
    await job.run(backfill_days=300)

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(run_liquidity_review_task())
