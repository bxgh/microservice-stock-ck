from typing import Dict, Any, Optional
from datetime import datetime
import logging

from ...models.monitor_models import ConnectionStats
from ...core.interfaces import ConnectionManagerInterface

logger = logging.getLogger(__name__)

class ConnectionMonitor:
    """
    连接状态监控器
    
    负责收集和标准化各个数据源的连接统计信息。
    """
    
    def __init__(self):
        self._managers: Dict[str, ConnectionManagerInterface] = {}
        
    def register(self, source_name: str, manager: ConnectionManagerInterface):
        """注册一个连接管理器进行监控"""
        self._managers[source_name] = manager
        logger.info(f"Registered connection monitor for: {source_name}")
        
    def unregister(self, source_name: str):
        """取消注册"""
        if source_name in self._managers:
            del self._managers[source_name]
            
    async def get_all_stats(self) -> Dict[str, Any]:
        """获取所有注册管理器的统计信息"""
        stats = {}
        for name, manager in self._managers.items():
            try:
                raw_stats = manager.get_stats()
                normalized = self._normalize_stats(name, raw_stats, manager.is_healthy())
                stats[name] = normalized.to_dict()
            except Exception as e:
                logger.error(f"Error getting stats for {name}: {e}")
                stats[name] = {"error": str(e)}
        return stats
        
    def _normalize_stats(self, name: str, raw_stats: Dict[str, Any], is_healthy: bool) -> ConnectionStats:
        """将原始统计字典转换为标准化模型"""
        
        # 提取通用字段
        total_creates = raw_stats.get('total_creates', 0)
        total_reuses = raw_stats.get('total_reuses', 0)
        total_errors = raw_stats.get('total_failures', 0)
        
        # 计算复用率
        reuse_rate = 0.0
        if 'reuse_rate' in raw_stats:
            # 如果已经是字符串 "99.0%"，尝试解析
            if isinstance(raw_stats['reuse_rate'], str) and raw_stats['reuse_rate'].endswith('%'):
                try:
                    reuse_rate = float(raw_stats['reuse_rate'].rstrip('%'))
                except ValueError:
                    pass
            elif isinstance(raw_stats['reuse_rate'], (int, float)):
                reuse_rate = float(raw_stats['reuse_rate'])
        
        # 处理连接池相关字段
        pool_size = raw_stats.get('pool_size', 1)  # 默认为1（单连接）
        active = raw_stats.get('active_connections', 0)
        idle = raw_stats.get('idle_connections', 0)
        
        # 如果是单连接模式（如Mootdx），根据连接状态推断
        if 'pool_size' not in raw_stats:
            active = 1 if is_healthy else 0
            idle = 0
            
        return ConnectionStats(
            source_name=name,
            is_connected=is_healthy,
            pool_size=pool_size,
            active_connections=active,
            idle_connections=idle,
            total_creates=total_creates,
            total_reuses=total_reuses,
            total_errors=total_errors,
            reuse_rate=reuse_rate,
            last_activity=datetime.now()
        )

    async def warmup_all(self):
        """预热所有连接池"""
        logger.info("🔥 Warming up all connection pools...")
        for name, manager in self._managers.items():
            try:
                success = await manager.initialize()
                if success:
                    logger.info(f"  ✅ {name} initialized")
                else:
                    logger.warning(f"  ⚠️ {name} initialization returned False")
            except Exception as e:
                logger.error(f"  ❌ {name} warmup failed: {e}")

    async def cooldown_all(self):
        """冷却所有连接池"""
        logger.info("❄️ Cooling down all connection pools...")
        for name, manager in self._managers.items():
            try:
                await manager.cleanup()
                logger.info(f"  ✅ {name} cleaned up")
            except Exception as e:
                logger.error(f"  ❌ {name} cooldown failed: {e}")

# 全局单例
connection_monitor = ConnectionMonitor()
