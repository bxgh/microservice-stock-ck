import logging
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    应用配置类，从 .env 文件或环境变量加载配置信息。
    配置项名称需与 .env 中的全大写变量名一致。
    """
    PROJECT_NAME: str = "altdata-source"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    PORT: int = 8011

    # Nacos 注册中心配置
    NACOS_HOST: str = "127.0.0.1"
    NACOS_PORT: int = 8848
    NACOS_NAMESPACE: str = "public"

    # ClickHouse Config (使用 8123 提供 HTTP)
    CLICKHOUSE_HOST: str = "127.0.0.1"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_DB: str = "altdata"

    # GitHub 采集特定配置
    GITHUB_TOKENS: str = ""  # 逗号分隔的多个 token
    
    @property
    def github_token_list(self) -> List[str]:
        """将配置的 token 字符串解析为列表"""
        if not self.GITHUB_TOKENS:
            return []
        return [t.strip() for t in self.GITHUB_TOKENS.split(",") if t.strip()]

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"


# 全局单例
settings = Settings()

# 全局日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(settings.PROJECT_NAME)
