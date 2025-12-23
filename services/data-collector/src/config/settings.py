"""
Data Collector 配置设置
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 服务配置
    name: str = "DataCollector"
    version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8089
    
    # Nacos 配置
    nacos_server: str = "nacos:8848"
    nacos_namespace: str = ""
    
    # ClickHouse 配置
    clickhouse_host: str = "microservice-stock-clickhouse"
    clickhouse_port: int = 9000
    clickhouse_database: str = "stock_data"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    
    # 腾讯云 MySQL 配置
    mysql_host: str = ""
    mysql_port: int = 3306
    mysql_database: str = "stock_data"
    mysql_user: str = ""
    mysql_password: str = ""
    
    # Redis 配置
    redis_host: str = "microservice-stock-redis"
    redis_port: int = 6379
    redis_password: str = "redis123"
    
    # 采集配置
    batch_size: int = 100  # 批量采集股票数
    max_workers: int = 5   # 并发采集数
    datasource_url: str = "mootdx-source:50051"  # 数据源 gRPC 地址
    
    class Config:
        env_file = ".env"
        env_prefix = "DC_"
        extra = "ignore"


settings = Settings()
