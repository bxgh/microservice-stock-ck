from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Config
    ENV: str = "dev"
    NAME: str = "CCI-Monitor"
    VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Server Config
    HOST: str = "0.0.0.0"
    PORT: int = 8085
    
    # MySQL Database Config (Reusing node 41 tunnel)
    DB_TYPE: str = "mysql"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 36301
    DB_USER: str = "root"
    DB_PASSWORD: str = "alwaysup@888"
    DB_NAME: str = "alwaysup"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    
    # Data API Config (get-stockdata)
    GSD_API_URL: str = "http://127.0.0.1:8000"
    GSD_API_TIMEOUT: int = 30
    
    # Nacos Config
    NACOS_SERVER_URL: str = "http://127.0.0.1:8848"
    NACOS_NAMESPACE: str = "public"
    NACOS_GROUP: str = "DEFAULT_GROUP"
    ENABLE_NACOS: bool = False
    
    # CCI Calculation Settings (Defaults from specs.md)
    CCI_WINDOW_DAYS: int = 20
    CCI_SMOOTH_DAYS: int = 5
    CCI_CRITICAL_THRESHOLD: float = 0.5
    
    # Cache Settings
    DATA_CACHE_DIR: str = "/app/data/cache"
    CACHE_DEFAULT_TTL: int = 24
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CCI_",
        extra="ignore"
    )

settings = Settings()
