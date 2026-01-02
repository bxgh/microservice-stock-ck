from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Orchestrator Configuration"""
    
    # Service
    APP_NAME: str = "Task Orchestrator"
    DEBUG: bool = False
    
    # Docker
    DOCKER_HOST: str = "unix:///var/run/docker.sock"
    WORKER_IMAGE: str = "gsd-worker:latest"
    WORKER_NETWORK: str = "stock_data_network"
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 1  # Use DB 1 for orchestrator state
    
    # Worker DB Config (Injected into workers)
    # Tencent Cloud MySQL via GOST Tunnel
    WORKER_MYSQL_HOST: str = "127.0.0.1"
    WORKER_MYSQL_PORT: int = 36301
    WORKER_MYSQL_USER: str = "root"
    WORKER_MYSQL_PASSWORD: str = "alwaysup@888"
    WORKER_MYSQL_DATABASE: str = "alwaysup"
    
    WORKER_CLICKHOUSE_HOST: str = "127.0.0.1"
    WORKER_CLICKHOUSE_PORT: int = 9000
    WORKER_CLICKHOUSE_USER: str = "default"
    WORKER_CLICKHOUSE_PASSWORD: str = ""
    WORKER_CLICKHOUSE_DATABASE: str = "stock_data"
    
    TIMEZONE: str = "Asia/Shanghai"
    
    # Trading Hours
    MARKET_CLOSE_TIME: str = "15:00"
    SYNC_START_TIME: str = "15:05"  # Start slightly after close
    
    # Notifications
    NOTIFIER_WEBHOOK_URL: Optional[str] = None
    NOTIFIER_FEEDBACK_BOT_URL: Optional[str] = None # For interactive feedback later
    
    class Config:
        env_file = ".env"
        env_prefix = "ORCHESTRATOR_"

settings = Settings()
