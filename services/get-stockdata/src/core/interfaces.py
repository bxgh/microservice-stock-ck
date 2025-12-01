from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class ConnectionManagerInterface(ABC):
    """
    统一的连接管理接口
    
    所有数据源的连接管理类（如 MootdxConnection, TongDaXinClient）都应实现此接口，
    以便上层业务逻辑可以统一处理连接的生命周期。
    """
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        初始化连接管理器
        
        建立初始连接或初始化连接池。
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    async def get_connection(self) -> Any:
        """
        获取一个可用连接
        
        如果是单连接模式，返回当前连接；
        如果是连接池模式，从池中借出一个连接。
        
        Returns:
            Any: 连接对象（具体类型取决于数据源）
        """
        pass
    
    @abstractmethod
    async def release_connection(self, connection: Any) -> None:
        """
        释放连接
        
        Args:
            connection: 要释放的连接对象
            
        如果是连接池模式，将连接归还给池；
        如果是单连接模式，通常不需要做任何操作，或者根据策略关闭连接。
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """
        清理所有资源
        
        关闭所有活动连接，释放系统资源。通常在系统关闭时调用。
        """
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """
        检查管理器健康状态
        
        Returns:
            bool: 如果连接可用且健康，返回 True
        """
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        获取连接统计信息
        
        Returns:
            Dict[str, Any]: 包含连接数、复用率、错误数等统计信息
        """
        pass
