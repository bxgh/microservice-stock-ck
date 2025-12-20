"""
Data Source Package
数据源能力定义和路由辅助模块

结构:
- enums.py: DataSource, DataType 枚举
- capability.py: DataSourceCapability 数据类
- registry.py: CAPABILITIES, FALLBACK_CHAINS 配置
- helpers.py: 辅助函数

使用示例:
    from ds_registry import DataSource, DataType, get_primary_source, recommend_source
    
    # 获取 QUOTES 的主数据源
    source = get_primary_source(DataType.QUOTES)  # -> DataSource.MOOTDX
    
    # 推荐数据源（优先本地）
    source = recommend_source(DataType.FINANCE, prefer_local=True)
"""

# 枚举
from .enums import DataSource, DataType

# 数据类
from .capability import DataSourceCapability

# 注册表
from .registry import CAPABILITIES, FALLBACK_CHAINS

# 辅助函数
from .helpers import (
    get_capability,
    get_sources_for_type,
    get_fallback_chain,
    get_primary_source,
    get_fallback_source,
    get_local_sources,
    get_cloud_sources,
    recommend_source,
    print_capability_matrix,
)


__all__ = [
    # 枚举
    "DataSource",
    "DataType",
    # 数据类
    "DataSourceCapability",
    # 注册表
    "CAPABILITIES",
    "FALLBACK_CHAINS",
    # 辅助函数
    "get_capability",
    "get_sources_for_type",
    "get_fallback_chain",
    "get_primary_source",
    "get_fallback_source",
    "get_local_sources",
    "get_cloud_sources",
    "recommend_source",
    "print_capability_matrix",
]
