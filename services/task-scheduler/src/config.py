"""
TaskScheduler 微服务配置管理
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    app_name: str = Field(default="TaskScheduler", env="APP_NAME")
    app_version: str = Field(default="2.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # 服务配置
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8080, env="PORT")
    workers: int = Field(default=1, env="WORKERS")

    # 数据库配置
    mysql_host: str = Field(..., env="MYSQL_HOST")
    mysql_port: int = Field(default=3306, env="MYSQL_PORT")
    mysql_database: str = Field(..., env="MYSQL_DATABASE")
    mysql_user: str = Field(..., env="MYSQL_USER")
    mysql_password: str = Field(..., env="MYSQL_PASSWORD")

    @property
    def mysql_url(self) -> str:
        return f"mysql+asyncpg://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"

    # Redis 配置
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ClickHouse 配置
    clickhouse_host: str = Field(default="localhost", env="CLICKHOUSE_HOST")
    clickhouse_port: int = Field(default=8123, env="CLICKHOUSE_PORT")
    clickhouse_user: str = Field(default="default", env="CLICKHOUSE_USER")
    clickhouse_password: Optional[str] = Field(default=None, env="CLICKHOUSE_PASSWORD")
    clickhouse_database: str = Field(default="default", env="CLICKHOUSE_DATABASE")

    # 代理配置
    http_proxy: Optional[str] = Field(default=None, env="HTTP_PROXY")
    https_proxy: Optional[str] = Field(default=None, env="HTTPS_PROXY")

    # 时区配置
    timezone: str = Field(default="Asia/Shanghai", env="TIMEZONE")

    # 安全配置
    secret_key: str = Field(..., env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # 调度器配置
    scheduler_timezone: str = Field(default="Asia/Shanghai", env="SCHEDULER_TIMEZONE")
    max_workers: int = Field(default=10, env="MAX_WORKERS")
    job_defaults_coalesce: bool = Field(default=True, env="JOB_DEFAULTS_COALESCE")
    job_defaults_max_instances: int = Field(default=1, env="JOB_DEFAULTS_MAX_INSTANCES")

    # 监控配置
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局配置实例
settings = Settings()

# 日志配置
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(module)s %(funcName)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": settings.log_level,
            "formatter": "default",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.log_level,
            "formatter": "detailed",
            "filename": "logs/taskscheduler.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        },
        "json_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.log_level,
            "formatter": "json",
            "filename": "logs/taskscheduler.json",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "loggers": {
        "": {  # root logger
            "level": settings.log_level,
            "handlers": ["console", "file", "json_file"]
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False
        },
        "sqlalchemy": {
            "level": "WARNING",
            "handlers": ["file"],
            "propagate": False
        }
    }
}