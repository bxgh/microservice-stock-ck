from typing import Any, Dict, Optional
from core.interfaces import ConnectionManagerInterface
from services.tongdaxin_client import TongDaXinClient

class TongDaXinConnectionAdapter(ConnectionManagerInterface):
    """
    TongDaXinClient 的适配器
    
    将 TongDaXinClient 适配到 ConnectionManagerInterface 接口，
    使其可以被统一管理。
    """
    
    def __init__(self, client: TongDaXinClient):
        self.client = client
        
    async def initialize(self) -> bool:
        """初始化连接池"""
        return await self.client.initialize()
        
    async def get_connection(self) -> Any:
        """
        获取一个可用连接
        
        注意：调用了 client 的受保护方法 _get_connection
        """
        return await self.client._get_connection()
        
    async def release_connection(self, connection: Any) -> None:
        """
        释放连接
        
        注意：调用了 client 的受保护方法 _release_connection
        """
        await self.client._release_connection(connection)
        
    async def cleanup(self) -> None:
        """清理所有资源"""
        await self.client.close()
        
    def is_healthy(self) -> bool:
        """检查健康状态"""
        return self.client._is_connected
        
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        # 由于 get_status 是异步的，这里只能返回当前内存中的状态
        # 或者我们可以在这里不做复杂的统计，只返回基础信息
        return {
            'is_connected': self.client._is_connected,
            'pool_size': len(self.client._connection_pool),
            'max_connections': self.client.max_connections,
            'active_connections': sum(1 for c in self.client._connection_pool if c['in_use'])
        }
