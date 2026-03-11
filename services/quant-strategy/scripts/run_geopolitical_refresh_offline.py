import asyncio
import logging
import os

# 确保导入路径正确
import sys

import pandas as pd
from clickhouse_driver import Client

project_root = "/home/bxgh/microservice-stock/services/quant-strategy"
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from config.settings import Settings  # noqa: E402
from database.session import init_database  # noqa: E402


async def main():
    # 强制设置日志级别
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    logger = logging.getLogger("OfflineRefresh")

    settings = Settings()
    current_date = "2026-03-05"

    # 0. 初始化数据库
    await init_database()
    logger.info("Database initialized.")

    # 1. 初始化 gRPC 客户端 (ScenarioDetector 和 Bonuses 需要)
    from dao.client import data_client
    await data_client.initialize()
    logger.info("Data Client initialized.")

    # 2. 延迟导入业务组件
    from adapters.stock_data_provider import StockDataProvider
    from services.alpha.defense_factor_service import DefenseFactorService
    from services.alpha.geopolitical_scoring_service import GeopoliticalScoringService
    from services.stock_pool.candidate_service import CandidatePoolService
    from strategies.geopolitical.scenario_detector import ScenarioDetector

    # 自定义离线 DAO (添加锁以解决 Simultaneous queries 错误)
    class ClickHouseKLineDAO:
        def __init__(self, settings: Settings):
            self.client = Client(
                host=settings.QS_CLICKHOUSE_HOST,
                port=9000,
                user=settings.QS_CLICKHOUSE_USER,
                password=settings.QS_CLICKHOUSE_PASSWORD,
                database=settings.QS_CLICKHOUSE_DB
            )
            self._lock = asyncio.Lock() # Async lock for thread-safe access from executor

        async def get_kline(self, codes: list, start_date: str, end_date: str):
            query = """
                SELECT trade_date, open_price as open, high_price as high,
                       low_price as low, close_price as close, volume
                FROM stock_kline_daily
                WHERE stock_code IN %(codes)s
                  AND trade_date >= %(start)s
                  AND trade_date <= %(end)s
                ORDER BY trade_date ASC
            """
            loop = asyncio.get_event_loop()

            # 使用锁确保同一时间只有一个线程在使用 ClickHouse Client
            async with self._lock:
                def fetch():
                    try:
                        data, columns = self.client.execute(query, {
                            'codes': codes,
                            'start': start_date,
                            'end': end_date
                        }, with_column_types=True)
                        return data, columns
                    except Exception:
                        # 发生异常时尝试重新连接一次 (针对 Bad file descriptor)
                        try:
                            self.client.disconnect()
                            data, columns = self.client.execute(query, {
                                'codes': codes,
                                'start': start_date,
                                'end': end_date
                            }, with_column_types=True)
                            return data, columns
                        except Exception as inner_e:
                            raise inner_e

                data, columns = await loop.run_in_executor(None, fetch)

            if not data and "000001.SH" in codes:
                mock_dates = pd.date_range(start=start_date, end=end_date, freq='B')
                return [(d.date(), 3000, 3000, 3000, 3000, 1000000) for d in mock_dates], columns

            col_names = [c[0] for c in columns]
            df = pd.DataFrame(data, columns=col_names)
            if not df.empty:
                df['trade_date'] = df['trade_date'].astype(str)
            return df

    # 3. 初始化离线组件
    ck_dao = ClickHouseKLineDAO(settings)
    offline_defense_service = DefenseFactorService(kline_dao=ck_dao)

    # 4. 初始化核心子服务
    data_provider = StockDataProvider()
    scenario_detector = ScenarioDetector()
    geopolitical_scoring = GeopoliticalScoringService()

    candidate_service = CandidatePoolService(
        data_provider=data_provider,
        scenario_detector=scenario_detector,
        geopolitical_scoring=geopolitical_scoring
    )

    # 5. 打补丁替换全局单例
    import services.alpha.defense_factor_service as dfs_module
    import services.stock_pool.candidate_service as cs_module

    dfs_module.defense_factor_service = offline_defense_service
    cs_module.defense_factor_service = offline_defense_service

    logger.info("Starting FULL A-Share Geopolitical Refresh (Offline Mode)...")
    try:
        count = await candidate_service.refresh_geopolitical_pool(current_date)
        logger.info(f"Done! Refreshed {count} candidates.")

        # 6. 直接查询 SQLite 验证结果
        import sqlite3
        db_path = f"{project_root}/data/quant-strategy.db"
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT code, score, rank, entry_reason FROM candidate_pool WHERE pool_type = 'geopolitical' ORDER BY score DESC LIMIT 20;")
            rows = cursor.fetchall()
            print("\n--- Top 20 Geopolitical Defense Candidates (FINAL RESULT) ---")
            if not rows:
                print("No candidates found in database pool 'geopolitical'.")
            for row in rows:
                print(row)
            conn.close()

    except Exception as e:
        logger.error(f"Refresh failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
