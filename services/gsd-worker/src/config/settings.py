"""
应用配置设置
"""

import os
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older Pydantic V1 or if pydantic-settings missing
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 服务配置
    name: str = "GetStockData"
    version: str = "1.0.0"
    debug: bool = False

    # API配置
    host: str = "0.0.0.0"
    port: int = 8086
    workers: int = 1
    access_log: bool = True

    # 安全配置
    api_key: Optional[str] = None
    jwt_secret: Optional[str] = None
    token_expire_hours: int = 24

    # 数据库配置
    database_type: str = "sqlite"  # sqlite, mysql
    database_path: str = "data/getstockdata.db"
    
    # MySQL配置
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "stock_data"
    
    connection_pool_size: int = 10
    
    @property
    def database_url(self) -> str:
        """获取数据库连接URL"""
        if self.database_type == "mysql":
            from urllib.parse import quote_plus
            # 构建 MySQL 异步连接 URL (使用 aiomysql 或 asyncmy)
            # 必须对密码进行 URL 编码，防止特殊字符（如 @）破坏连接字符串
            encoded_user = quote_plus(self.db_user)
            encoded_password = quote_plus(self.db_password)
            
            return (
                f"mysql+aiomysql://{encoded_user}:{encoded_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
                "?charset=utf8mb4"
            )
        else:
            # 默认 SQLite 异步连接
            return f"sqlite+aiosqlite:///{self.database_path}"

    # Redis配置
    redis_url: str = "redis://localhost:6379"
    redis_max_connections: int = 20
    redis_retry_on_timeout: bool = True

    # 股票数据配置
    stock_api_base_url: str = "https://api.example.com"
    stock_api_timeout: int = 30
    stock_cache_ttl: int = 300
    enable_stock_caching: bool = True

    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/getstockdata.log"
    log_max_size: str = "10MB"
    log_backup_count: int = 5

    # 监控配置
    monitoring_enabled: bool = True
    metrics_path: str = "/api/v1/metrics"
    health_check_interval: int = 30

    # 股票数据请求配置
    default_timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 5

    # K线同步调度配置
    kline_sync_history_buffer_min: int = 5
    kline_sync_sleep_check_interval_min: int = 15
    kline_sync_poll_interval_min: int = 2
    kline_sync_timeout_time: str = "21:00"
    kline_sync_min_records: int = 4800
    kline_sync_batch_size: int = 10000

    class Config:
        env_file = ".env"
        env_prefix = "GSD_"
        extra = "ignore"


# 全局配置实例
settings = Settings()