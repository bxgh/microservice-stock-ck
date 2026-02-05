"""
应用配置设置 - 量化策略服务
"""


from pydantic import BaseModel as BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 服务配置
    name: str = "QuantStrategyService"
    version: str = "1.0.0"
    debug: bool = False

    # API配置
    host: str = "0.0.0.0"
    port: int = 8084
    workers: int = 1
    access_log: bool = True

    # 安全配置
    api_key: str | None = None
    jwt_secret: str | None = None
    token_expire_hours: int = 24

    # 数据库配置
    database_type: str = "sqlite"  # sqlite or mysql
    database_path: str = "data/quant-strategy.db"

    # MySQL配置 (when database_type="mysql")
    db_host: str = "sh-cdb-h7flpxu4.sql.tencentcdb.com"
    db_port: int = 26300
    db_user: str = "root"
    db_password: str = "alwaysup@888"
    db_name: str = "alwaysup"

    connection_pool_size: int = 10

    # Redis配置
    redis_url: str = "redis://:redis123@localhost:6379"
    redis_max_connections: int = 20
    redis_retry_on_timeout: bool = True

    # 调度器配置
    timezone: str = "Asia/Shanghai"
    max_workers: int = 10

    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/quant-strategy.log"
    log_max_size: str = "10MB"
    log_backup_count: int = 5

    # 监控配置
    monitoring_enabled: bool = True
    metrics_path: str = "/api/v1/metrics"
    health_check_interval: int = 30

    # 策略执行配置
    default_timeout: int = 300
    max_retries: int = 3
    retry_delay: int = 60

    # 策略引擎配置
    max_concurrent_strategies: int = 20
    signal_window_seconds: int = 60
    backtest_enabled: bool = True

    # 数据源配置 (host network mode, service on port 8083)
    stockdata_service_url: str = "http://127.0.0.1:8083"

    # ClickHouse 配置 (新增)
    QS_CLICKHOUSE_HOST: str = "127.0.0.1"
    QS_CLICKHOUSE_PORT: int = 9000
    QS_CLICKHOUSE_USER: str = "default"
    QS_CLICKHOUSE_PASSWORD: str = ""
    QS_CLICKHOUSE_DB: str = "stock_data"

    # Risk Filter Thresholds (EPIC-002)
    # 状态过滤
    filter_st_stocks: bool = True
    filter_suspended_stocks: bool = True
    filter_delisted_stocks: bool = True

    # 流动性风控
    min_market_cap_billion: float = 30.0  # 最小市值 30亿
    min_avg_daily_volume_million: float = 20.0 # 最小日均成交额 2000万

    # 财务风控 (硬伤)
    max_goodwill_ratio: float = 0.30     # 商誉/净资产 > 30%
    max_pledge_ratio: float = 0.50       # 质押率 > 50%
    min_cashflow_quality: float = 0.50   # 经营现金流/净利润 < 0.5

    # Fundamental Scoring Weights (EPIC-002 Story 2.2)
    weight_profitability: float = 0.4
    weight_growth: float = 0.3
    weight_quality: float = 0.3

    # Absolute Scoring Thresholds (Fallback Mode)
    # Profitability
    roe_excellent: float = 0.15  # > 15%
    roe_good: float = 0.10
    roe_acceptable: float = 0.05

    # Growth
    growth_excellent: float = 0.20  # > 20% YoY
    growth_good: float = 0.10
    growth_acceptable: float = 0.05

    # Quality
    ocf_quality_excellent: float = 1.0  # OCF/NetProfit > 1.0
    ocf_quality_good: float = 0.8

    # Valuation Scoring (EPIC-002 Story 2.3)
    weight_pe_score: float = 0.5
    weight_pb_score: float = 0.5

    # Percentile Thresholds (Lower is better/cheaper)
    val_undervalued_pct: float = 25.0   # < 25% = 100 pts
    val_fair_low_pct: float = 50.0      # 25-50% = 80 pts
    val_fair_high_pct: float = 75.0     # 50-75% = 60 pts
    val_overvalued_pct: float = 90.0    # 75-90% = 40 pts
                                        # > 90% = 20 pts

    class Config:
        env_file = ".env"
        env_prefix = "QS_"


# 全局配置实例
settings = Settings()
