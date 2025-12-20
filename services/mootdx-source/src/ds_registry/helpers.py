"""
Data Source Helper Functions
数据源辅助函数

提供:
- 能力查询
- 路由建议
- 降级链查询
- 调试工具
"""
from typing import List, Optional
import logging

from .enums import DataSource, DataType
from .capability import DataSourceCapability
from .registry import CAPABILITIES, FALLBACK_CHAINS


logger = logging.getLogger("datasource-helpers")


def get_capability(source: DataSource) -> Optional[DataSourceCapability]:
    """获取指定数据源的能力定义"""
    return CAPABILITIES.get(source)


def get_sources_for_type(data_type: DataType) -> List[DataSource]:
    """
    获取支持指定数据类型的所有数据源（按可靠性排序）
    
    Args:
        data_type: 数据类型
    
    Returns:
        支持该类型的数据源列表，按可靠性降序排列
    """
    sources = [
        source for source, cap in CAPABILITIES.items()
        if data_type in cap.supported_types or data_type.value in cap.supported_types
    ]
    sources.sort(key=lambda s: CAPABILITIES[s].reliability, reverse=True)
    return sources


def get_fallback_chain(data_type: DataType) -> List[DataSource]:
    """获取数据类型的降级链"""
    return FALLBACK_CHAINS.get(data_type, [])


def get_primary_source(data_type: DataType) -> Optional[DataSource]:
    """获取数据类型的主数据源"""
    chain = get_fallback_chain(data_type)
    return chain[0] if chain else None


def get_fallback_source(data_type: DataType) -> Optional[DataSource]:
    """获取数据类型的降级数据源"""
    chain = get_fallback_chain(data_type)
    return chain[1] if len(chain) > 1 else None


def get_local_sources() -> List[DataSource]:
    """获取所有本地数据源（不需要外网）"""
    return [
        source for source, cap in CAPABILITIES.items()
        if not cap.requires_network
    ]


def get_cloud_sources() -> List[DataSource]:
    """获取所有云端数据源（需要外网）"""
    return [
        source for source, cap in CAPABILITIES.items()
        if cap.requires_network
    ]


def recommend_source(data_type: DataType, prefer_local: bool = True) -> DataSource:
    """
    推荐最佳数据源
    
    Args:
        data_type: 数据类型
        prefer_local: 是否优先本地数据源
    
    Returns:
        推荐的数据源
    """
    sources = get_sources_for_type(data_type)
    
    if not sources:
        logger.warning(f"No source found for {data_type}")
        return DataSource.ERROR
    
    if prefer_local:
        local = [s for s in sources if not CAPABILITIES[s].requires_network]
        if local:
            return local[0]
    
    return sources[0]


def print_capability_matrix():
    """打印能力矩阵（调试用）"""
    print("\n" + "=" * 80)
    print("数据源能力矩阵")
    print("=" * 80)
    
    # 表头
    print(f"{'数据类型':<15} {'主数据源':<20} {'降级数据源':<20} {'可靠性':<10}")
    print("-" * 80)
    
    for dt in DataType:
        primary = get_primary_source(dt)
        fallback = get_fallback_source(dt)
        
        primary_name = CAPABILITIES[primary].display_name if primary else "-"
        fallback_name = CAPABILITIES[fallback].display_name if fallback else "无"
        reliability = f"{CAPABILITIES[primary].reliability:.0%}" if primary else "-"
        
        print(f"{dt.value:<15} {primary_name:<20} {fallback_name:<20} {reliability:<10}")
    
    print("=" * 80)
