"""
应用配置设置 - 量化策略服务
"""

from typing import Optional
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
    api_key: Optional[str] = None
    jwt_secret: Optional[str] = None
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

    class Config:
        env_file = ".env"
        env_prefix = "QS_"


# 全局配置实例
settings = Settings()
