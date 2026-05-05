import asyncio
import httpx
import logging
import os

# Configuration
CH_HOST = os.environ.get("CLICKHOUSE_HOST", "127.0.0.1")
# Force HTTP port 8123, ignoring TCP port 9000 in env
CH_PORT = os.environ.get("CLICKHOUSE_HTTP_PORT", "8123")
CH_DB = os.environ.get("CLICKHOUSE_DB", "stock_data")
CH_URL = f"http://{CH_HOST}:{CH_PORT}/"
CLUSTER = "stock_cluster"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DDL_STATEMENTS = [
    # 1. Financial Data
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_financial_local (
        `stock_code` String,
        `report_date` Date,
        `total_revenue` Nullable(Float64),
        `net_profit` Nullable(Float64),
        `roe` Nullable(Float64),
        `earnings_per_share` Nullable(Float64),
        `update_time` DateTime DEFAULT now()
    ) ENGINE = ReplacingMergeTree(update_time)
    ORDER BY (stock_code, report_date)
    """,
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_financial AS {db}.stock_financial_local
    ENGINE = Distributed('{cluster}', '{db}', 'stock_financial_local', xxHash64(stock_code))
    """,

    # 2. Valuation Logic
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_valuation_local (
        `stock_code` String,
        `trade_date` Date,
        `pe` Nullable(Float64),
        `pb` Nullable(Float64),
        `ps` Nullable(Float64),
        `market_cap` Nullable(Float64),
        `price` Nullable(Float64),
        `update_time` DateTime DEFAULT now()
    ) ENGINE = ReplacingMergeTree(update_time)
    PARTITION BY toYYYYMM(trade_date)
    ORDER BY (stock_code, trade_date)
    """,
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_valuation AS {db}.stock_valuation_local
    ENGINE = Distributed('{cluster}', '{db}', 'stock_valuation_local', xxHash64(stock_code))
    """,

    # 3. Capital Flow
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_capital_flow_local (
        `stock_code` String,
        `trade_date` Date,
        `close` Nullable(Float64),
        `main_net_inflow` Nullable(Float64),
        `main_net_inflow_pct` Nullable(Float64),
        `super_large_net_inflow` Nullable(Float64),
        `large_net_inflow` Nullable(Float64),
        `medium_net_inflow` Nullable(Float64),
        `small_net_inflow` Nullable(Float64),
        `update_time` DateTime DEFAULT now()
    ) ENGINE = ReplacingMergeTree(update_time)
    PARTITION BY toYYYYMM(trade_date)
    ORDER BY (stock_code, trade_date)
    """,
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_capital_flow AS {db}.stock_capital_flow_local
    ENGINE = Distributed('{cluster}', '{db}', 'stock_capital_flow_local', xxHash64(stock_code))
    """,

    # 4. Dividend
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_dividend_local (
        `stock_code` String,
        `report_date` Date,
        `plan_date` Nullable(Date),
        `bonus_share_ratio` Nullable(Float64),
        `cash_dividend_ratio` Nullable(Float64),
        `progress` String,
        `update_time` DateTime DEFAULT now()
    ) ENGINE = ReplacingMergeTree(update_time)
    ORDER BY (stock_code, report_date)
    """,
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_dividend AS {db}.stock_dividend_local
    ENGINE = Distributed('{cluster}', '{db}', 'stock_dividend_local', xxHash64(stock_code))
    """,

    # 5. Shareholder - Count
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_holder_count_local (
        `stock_code` String,
        `report_date` Date,
        `holder_count` Int64,
        `change` Nullable(Int64),
        `avg_market_cap` Nullable(Float64),
        `update_time` DateTime DEFAULT now()
    ) ENGINE = ReplacingMergeTree(update_time)
    ORDER BY (stock_code, report_date)
    """,
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_holder_count AS {db}.stock_holder_count_local
    ENGINE = Distributed('{cluster}', '{db}', 'stock_holder_count_local', xxHash64(stock_code))
    """,

    # 6. Shareholder - Top 10
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_top_holders_local (
        `stock_code` String,
        `report_date` Date,
        `rank` Int8,
        `holder_name` String,
        `hold_count` Nullable(Float64),
        `hold_pct` Nullable(Float64),
        `share_type` String,
        `update_time` DateTime DEFAULT now()
    ) ENGINE = ReplacingMergeTree(update_time)
    ORDER BY (stock_code, report_date, rank)
    """,
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_top_holders AS {db}.stock_top_holders_local
    ENGINE = Distributed('{cluster}', '{db}', 'stock_top_holders_local', xxHash64(stock_code))
    """,

    # 7. Block Trade
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_block_trade_local (
        `stock_code` String,
        `trade_date` Date,
        `price` Float64,
        `volume` Float64,
        `amount` Float64,
        `buyer` String,
        `seller` String,
        `update_time` DateTime DEFAULT now()
    ) ENGINE = ReplacingMergeTree(update_time)
    PARTITION BY toYYYYMM(trade_date)
    ORDER BY (stock_code, trade_date, price, buyer, seller)
    """,
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_block_trade AS {db}.stock_block_trade_local
    ENGINE = Distributed('{cluster}', '{db}', 'stock_block_trade_local', xxHash64(stock_code))
    """,

    # 8. Margin
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_margin_local (
        `stock_code` String,
        `trade_date` Date,
        `rz_balance` Nullable(Float64),
        `rq_balance` Nullable(Float64),
        `rz_buy` Nullable(Float64),
        `rz_repay` Nullable(Float64),
        `rq_sell` Nullable(Float64),
        `rq_repay` Nullable(Float64),
        `update_time` DateTime DEFAULT now()
    ) ENGINE = ReplacingMergeTree(update_time)
    PARTITION BY toYYYYMM(trade_date)
    ORDER BY (stock_code, trade_date)
    """,
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_margin AS {db}.stock_margin_local
    ENGINE = Distributed('{cluster}', '{db}', 'stock_margin_local', xxHash64(stock_code))
    """,

    # 9. Stock Top List (Dragon Tiger)
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_top_list_local (
        `stock_code` String,
        `trade_date` Date,
        `reason` String,
        `net_buy` Nullable(Float64),
        `turnover_rate` Nullable(Float64),
        `close_price` Nullable(Float64),
        `change_pct` Nullable(Float64),
        `update_time` DateTime DEFAULT now()
    ) ENGINE = ReplacingMergeTree(update_time)
    PARTITION BY toYYYYMM(trade_date)
    ORDER BY (stock_code, trade_date, reason)
    """,
    """
    CREATE TABLE IF NOT EXISTS {db}.stock_top_list AS {db}.stock_top_list_local
    ENGINE = Distributed('{cluster}', '{db}', 'stock_top_list_local', xxHash64(stock_code))
    """
]

async def create_tables():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check connection
        try:
            await client.get(CH_URL)
            logger.info(f"Connected to ClickHouse at {CH_URL}")
        except Exception as e:
            logger.error(f"Cannot connect to ClickHouse: {e}")
            return

        for ddl in DDL_STATEMENTS:
            sql = ddl.format(db=CH_DB, cluster=CLUSTER).strip()
            table_name = sql.split()[5] if "CREATE TABLE IF NOT EXISTS" in sql else "unknown"
            
            logger.info(f"Executing DDL for table: {table_name}")
            try:
                resp = await client.post(CH_URL, params={"query": sql})
                if resp.status_code == 200:
                    logger.info("  -> Success")
                else:
                    logger.error(f"  -> Error {resp.status_code}: {resp.text}")
            except Exception as e:
                logger.error(f"  -> Execution Failed: {e}")

if __name__ == "__main__":
    asyncio.run(create_tables())
