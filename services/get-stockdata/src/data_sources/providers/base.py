# -*- coding: utf-8 -*-
"""
EPIC-007 数据提供者核心模块

定义数据提供者的抽象接口、数据类型枚举和标准返回格式。
所有数据源实现必须继承 DataProvider 基类。

@author: EPIC-007
@date: 2025-12-06
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd


class DataType(Enum):
    """数据类型枚举
    
    用于标识数据源支持的能力和路由数据请求。
    """
    QUOTES = "quotes"         # 实时行情
    TICK = "tick"             # 分笔成交
    HISTORY = "history"       # 历史K线
    RANKING = "ranking"       # 榜单数据 (涨停池、龙虎榜、人气榜)
    SECTOR = "sector"         # 板块数据 (行业/概念涨幅)
    INDEX = "index"           # 指数成分
    SCREENING = "screening"   # 自然语言选股
    META = "meta"             # 股票元信息 (名称、市值等)
    FINANCIAL = "financial"   # 财务报表
    FUND_FLOW = "fund_flow"   # 资金流向
    FINANCE = "finance"       # 财务报表 (EPIC-002)
    VALUATION = "valuation"   # 估值数据 (EPIC-002)
    INDUSTRY = "industry"     # 行业数据 (EPIC-002)


@dataclass
class DataResult:
    """标准化数据返回格式
    
    所有数据提供者的 fetch 方法都返回此格式,确保上层代码可以统一处理。
    
    Attributes:
        success: 是否成功获取数据
        data: 获取到的数据 (DataFrame)
        provider: 实际使用的数据源名称
        data_type: 数据类型
        latency_ms: 获取延迟 (毫秒)
        is_cache: 是否来自缓存
        is_fallback: 是否使用了降级数据源
        error: 错误信息 (如有)
        timestamp: 数据获取时间
        extra: 额外元信息
    """
    success: bool
    data: Optional[pd.DataFrame] = None
    provider: str = ""
    data_type: DataType = DataType.QUOTES
    latency_ms: float = 0.0
    is_cache: bool = False
    is_fallback: bool = False
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    extra: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def row_count(self) -> int:
        """数据行数"""
        return len(self.data) if self.data is not None else 0
    
    @property
    def is_empty(self) -> bool:
        """数据是否为空"""
        return self.data is None or len(self.data) == 0
    
    def __repr__(self) -> str:
        status = "✅" if self.success else "❌"
        return (f"DataResult({status} {self.provider}/{self.data_type.value}: "
                f"{self.row_count} rows, {self.latency_ms:.1f}ms"
                f"{', fallback' if self.is_fallback else ''}"
                f"{', cache' if self.is_cache else ''})")


class DataProvider(ABC):
    """数据提供者抽象基类
    
    所有数据源实现必须继承此类并实现抽象方法。
    框架通过此接口实现数据源的统一管理和自动降级。
    
    设计原则:
    1. 单一职责: 每个 Provider 只负责一个数据源
    2. 声明能力: 通过 capabilities 声明支持的数据类型
    3. 统一接口: 通过 fetch 方法统一获取数据
    4. 可扩展: 新数据源只需实现此接口即可接入
    
    Example:
        class MootdxProvider(DataProvider):
            @property
            def name(self) -> str:
                return "mootdx"
            
            @property
            def capabilities(self) -> List[DataType]:
                return [DataType.QUOTES, DataType.TICK, DataType.HISTORY]
            
            async def fetch(self, data_type: DataType, **kwargs) -> DataResult:
                if data_type == DataType.QUOTES:
                    return await self._fetch_quotes(**kwargs)
                ...
    """
    
    # ========== 元信息 ==========
    
    @property
    @abstractmethod
    def name(self) -> str:
        """数据源唯一标识名称
        
        用于日志、监控和配置引用。应为小写字母和下划线。
        
        Returns:
            str: 如 "mootdx", "akshare", "pywencai"
        """
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> List[DataType]:
        """声明支持的数据类型列表
        
        框架根据此列表进行路由:
        - QuotesService 会选择 capabilities 包含 QUOTES 的 Provider
        - RankingService 会选择 capabilities 包含 RANKING 的 Provider
        
        Returns:
            List[DataType]: 支持的数据类型列表
        """
        pass
    
    @property
    def priority_map(self) -> Dict[DataType, int]:
        """各数据类型的优先级 (数字越小优先级越高)
        
        默认所有能力优先级为 10。子类可覆盖以调整优先级。
        
        示例:
            mootdx 的 QUOTES 优先级为 1 (首选)
            easyquotation 的 QUOTES 优先级为 2 (备选)
        
        Returns:
            Dict[DataType, int]: 数据类型 -> 优先级映射
        """
        return {dt: 10 for dt in self.capabilities}
    
    @property
    def requires_proxy(self) -> bool:
        """是否需要特殊代理 (如 proxychains4)
        
        baostock 等需要特殊网络配置的数据源应返回 True。
        
        Returns:
            bool: 是否需要代理
        """
        return False
    
    # ========== 生命周期 ==========
    
    async def initialize(self) -> bool:
        """初始化连接
        
        在首次使用前调用。可用于建立连接、预热缓存等。
        默认返回 True, 子类可覆盖实现具体逻辑。
        
        Returns:
            bool: 初始化是否成功
        """
        return True
    
    async def close(self) -> None:
        """关闭连接
        
        在服务关闭时调用。应释放所有资源。
        默认无操作, 子类可覆盖实现具体逻辑。
        """
        pass
    
    async def health_check(self) -> bool:
        """健康检查
        
        检查数据源是否可用。用于降级决策。
        默认返回 True, 子类应覆盖实现实际检查。
        
        Returns:
            bool: 数据源是否健康
        """
        return True
    
    # ========== 数据获取 ==========
    
    @abstractmethod
    async def fetch(self, data_type: DataType, **kwargs) -> DataResult:
        """统一数据获取入口
        
        框架通过此方法获取数据。子类根据 data_type 路由到具体实现。
        
        Args:
            data_type: 请求的数据类型
            **kwargs: 数据类型特定的参数, 如:
                - QUOTES: codes=["000001", "600519"]
                - HISTORY: code="000001", start="2024-01-01", end="2024-12-06"
                - RANKING: ranking_type="limit_up", date="2024-12-06"
        
        Returns:
            DataResult: 标准化的返回结果
        
        Raises:
            NotImplementedError: 如果请求了不支持的数据类型
        """
        pass
    
    def supports(self, data_type: DataType) -> bool:
        """检查是否支持指定数据类型
        
        Args:
            data_type: 要检查的数据类型
        
        Returns:
            bool: 是否支持
        """
        return data_type in self.capabilities
    
    def get_priority(self, data_type: DataType) -> int:
        """获取指定数据类型的优先级
        
        Args:
            data_type: 数据类型
        
        Returns:
            int: 优先级 (数字越小越优先, 不支持返回 999)
        """
        return self.priority_map.get(data_type, 999)
    
    def __repr__(self) -> str:
        caps = ", ".join(dt.value for dt in self.capabilities)
        return f"<{self.__class__.__name__}({self.name}) caps=[{caps}]>"
