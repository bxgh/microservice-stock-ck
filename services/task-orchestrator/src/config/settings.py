from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Orchestrator Configuration"""
    
    # Service
    APP_NAME: str = "Task Orchestrator"
    DEBUG: bool = False
    
    # Base Directory (Dynamic)
    # This assumes the settings.py is in services/task-orchestrator/src/config/
    # So we go up 4 levels to get to the project root
    @property
    def BASE_DIR(self) -> str:
        env_base = os.getenv("ORCHESTRATOR_BASE_DIR")
        if env_base:
            return env_base
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    
    @property
    def HOST_BASE_DIR(self) -> str:
        """
        The project root path ON THE HOST machine. 
        Used for Docker volume mounting because the Docker daemon runs on the host.
        """
        return os.getenv("ORCHESTRATOR_HOST_BASE_DIR", self.BASE_DIR)
    
    # Docker
    DOCKER_HOST: str = "unix:///var/run/docker.sock"
    WORKER_IMAGE: str = "gsd-worker:latest"
    WORKER_NETWORK: str = "stock_data_network"
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD: str = "redis123"
    REDIS_DB: int = 1  # Use DB 1 for orchestrator state
    REDIS_CLUSTER: bool = False # Default to standalone
    
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
    
    WORKER_MOOTDX_API_URL: str = "http://mootdx-api:8000"  # 容器网络默认域名
    
    TIMEZONE: str = "Asia/Shanghai"
    
    # Trading Hours
    MARKET_CLOSE_TIME: str = "15:00"
    SYNC_START_TIME: str = "15:05"  # Start slightly after close
    
    # LLM settings
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    SILICONFLOW_API_KEY: Optional[str] = os.getenv("SILICONFLOW_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    LLM_DEFAULT_PROVIDER: str = "deepseek"
    
    # Notifications
    NOTIFIER_WEBHOOK_URL: Optional[str] = None
    NOTIFIER_FEEDBACK_BOT_URL: Optional[str] = None # For interactive feedback later
    
    class Config:
        env_file = ".env"
        env_prefix = "ORCHESTRATOR_"
        extra = "allow"
    
    # Orchestrator MySQL (for task logs)
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 36301  # GOST tunnel
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "alwaysup@888"
    MYSQL_DATABASE: str = "alwaysup"
    MYSQL_POOL_SIZE: int = 5

settings = Settings()
