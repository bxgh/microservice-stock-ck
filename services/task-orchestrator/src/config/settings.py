from pydantic_settings import BaseSettings
from pydantic import Field, AliasChoices
from typing import Optional
import os
from dotenv import load_dotenv

# 显式加载根目录 .env (如果存在)
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../../.env"))

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
    ENABLE_SILICONFLOW: bool = os.getenv("ORCHESTRATOR_ENABLE_SILICONFLOW", "true").lower() == "true"
    LLM_DEFAULT_PROVIDER: str = "deepseek"
    
    # Notifications
    NOTIFIER_WEBHOOK_URL: Optional[str] = None
    NOTIFIER_FEEDBACK_BOT_URL: Optional[str] = None # For interactive feedback later
    
    # Email Settings
    EMAIL_HOST: str = Field("smtp.qq.com", validation_alias=AliasChoices("ORCHESTRATOR_EMAIL_HOST", "SMTP_HOST"))
    EMAIL_PORT: int = Field(465, validation_alias=AliasChoices("ORCHESTRATOR_EMAIL_PORT", "SMTP_PORT"))
    EMAIL_USER: Optional[str] = Field(None, validation_alias=AliasChoices("ORCHESTRATOR_EMAIL_USER", "SMTP_USER"))
    EMAIL_PASSWORD: Optional[str] = Field(None, validation_alias=AliasChoices("ORCHESTRATOR_EMAIL_PASSWORD", "SMTP_PASS"))
    EMAIL_FROM: str = Field("system@alwaysup.com", validation_alias=AliasChoices("ORCHESTRATOR_EMAIL_FROM", "SMTP_USER"))
    EMAIL_TO: str = Field("admin@alwaysup.com", validation_alias=AliasChoices("ORCHESTRATOR_EMAIL_TO", "ALERT_RECEIVER"))
    
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
