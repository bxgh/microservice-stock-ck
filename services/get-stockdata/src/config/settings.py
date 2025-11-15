"""
应用配置设置
"""

import os
from typing import Optional
from pydantic import BaseModel as BaseSettings


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
    database_type: str = "sqlite"
    database_path: str = "data/getstockdata.db"
    connection_pool_size: int = 10

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

    class Config:
        env_file = ".env"
        env_prefix = "GSD_"


# 全局配置实例
settings = Settings()