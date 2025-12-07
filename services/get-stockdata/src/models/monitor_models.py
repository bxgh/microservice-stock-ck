from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any

@dataclass
class ConnectionStats:
    """连接统计信息标准模型"""
    source_name: str              # 数据源名称
    is_connected: bool            # 是否连接正常
    pool_size: int = 0            # 连接池大小
    active_connections: int = 0   # 当前活跃连接数
    idle_connections: int = 0     # 当前空闲连接数
    total_creates: int = 0        # 累计创建次数
    total_reuses: int = 0         # 累计复用次数
    total_errors: int = 0         # 累计错误次数
    reuse_rate: float = 0.0       # 复用率 (0-100%)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于API响应或日志"""
        return {
            "source_name": self.source_name,
            "status": "UP" if self.is_connected else "DOWN",
            "pool": {
                "total": self.pool_size,
                "active": self.active_connections,
                "idle": self.idle_connections
            },
            "metrics": {
                "creates": self.total_creates,
                "reuses": self.total_reuses,
                "errors": self.total_errors,
                "reuse_rate": f"{self.reuse_rate:.1f}%"
            },
            "timestamp": self.last_activity.isoformat()
        }
