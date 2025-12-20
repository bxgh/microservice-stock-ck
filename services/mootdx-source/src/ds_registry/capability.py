"""
Data Source Capability Definition
数据源能力定义
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class DataSourceCapability:
    """
    数据源能力定义
    
    Attributes:
        name: 数据源名称（英文标识）
        display_name: 显示名称（中文）
        supported_types: 支持的数据类型列表
        latency_ms: 延迟范围 (最小, 最大) 毫秒
        reliability: 可靠性评分 (0.0 - 1.0)
        requires_network: 是否需要外网访问
        rate_limit: 频率限制 (每分钟请求数, 0表示无限制)
        notes: 选择该数据源的理由说明
    """
    name: str
    display_name: str
    supported_types: Tuple[str, ...]
    latency_ms: Tuple[int, int]
    reliability: float
    requires_network: bool
    rate_limit: int  # 每分钟最大请求数, 0=无限制
    notes: str
