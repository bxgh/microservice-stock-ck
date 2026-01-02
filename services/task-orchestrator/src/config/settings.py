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
    REDIS_DB: int = 1  # Use DB 1 for orchestrator state
    
    # Trading Hours
    MARKET_CLOSE_TIME: str = "15:00"
    SYNC_START_TIME: str = "15:05"  # Start slightly after close
    
    class Config:
        env_file = ".env"
        env_prefix = "ORCHESTRATOR_"

settings = Settings()
