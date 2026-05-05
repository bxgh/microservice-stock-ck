import os
from dataclasses import dataclass
from datetime import datetime, timedelta

# 从 ds_registry 包导入 DataSource 枚举 (统一来源)
from ds_registry import DataSource


@dataclass(frozen=True)
class MySQLConfig:
    """MySQL 连接配置"""
    host: str = os.getenv("GSD_DB_HOST", "localhost")
    port: int = int(os.getenv("GSD_DB_PORT", 36301))
    user: str = os.getenv("GSD_DB_USER", "root")
    password: str = os.getenv("GSD_DB_PASSWORD", "")
    database: str = os.getenv("GSD_DB_NAME", "alwaysup")


@dataclass(frozen=True)
class ClickHouseConfig:
    """ClickHouse 连接配置"""
    host: str = os.getenv("CLICKHOUSE_HOST", "localhost")
    port: int = int(os.getenv("CLICKHOUSE_PORT", 9000))
    user: str = os.getenv("CLICKHOUSE_USER", "admin")
    password: str = os.getenv("CLICKHOUSE_PASSWORD", "admin123")
    database: str = os.getenv("CLICKHOUSE_DATABASE", "stock_data")


def get_default_date_range() -> tuple[str, str]:
    """
    获取默认日期范围：当前日期往前一年
    
    Returns:
        (start_date, end_date) 格式: "YYYY-MM-DD"
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


@dataclass(frozen=True)
class HistoryDefaults:
    """历史K线默认参数"""
    FREQUENCY: str = "d"  # d/w/m for daily/weekly/monthly
    ADJUST: str = "2"  # 1=后复权 2=前复权 3=不复权
    
    @staticmethod
    def get_start_date() -> str:
        """动态获取默认开始日期（一年前）"""
        return get_default_date_range()[0]
    
    @staticmethod
    def get_end_date() -> str:
        """动态获取默认结束日期（今天）"""
        return get_default_date_range()[1]


@dataclass(frozen=True)
class QueryDefaults:
    """查询默认参数"""
    PYWENCAI_DEFAULT_QUERY: str = "今日涨停"
    PYWENCAI_DEFAULT_PERPAGE: int = 20
    RANKING_DEFAULT_TYPE: str = "hot"


@dataclass(frozen=True)
class DragonTigerDefaults:
    """龙虎榜默认参数"""
    MARKET: str = "沪深"  # 市场类型：沪深/上海/深圳
    
    @staticmethod
    def get_default_date() -> str:
        """获取默认查询日期（昨天，因为龙虎榜通常T+1发布）"""
        yesterday = datetime.now() - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d")


@dataclass(frozen=True)
class RetryConfig:
    """重试配置"""
    MAX_ATTEMPTS: int = 3
    MIN_WAIT_SECONDS: float = 1.0
    MAX_WAIT_SECONDS: float = 10.0
    EXPONENTIAL_MULTIPLIER: float = 2.0
    
    # 云端API超时
    CLOUD_API_TIMEOUT: int = 30
    
    # 本地调用超时
    LOCAL_TIMEOUT: int = 10
