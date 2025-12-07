# Story 002-05: 连接状态监控

**Story ID**: STORY-002-05  
**Epic**: EPIC-002 高可用采集引擎  
**优先级**: P2  
**估算**: 1 天  
**状态**: ✅ 已完成  
**依赖**: Story 4 (统一接口)  
**实际完成时间**: 2025-11-29

---

## 📋 Story 概述

基于统一的 `ConnectionManagerInterface`，构建连接状态监控机制。使系统能够实时暴露连接池的健康状态、负载情况和性能指标，便于运维排查问题和优化配置。

### 业务价值
- **可观测性**: 实时了解连接池是否健康，是否有连接泄漏
- **故障排查**: 快速定位连接超时或失败的根本原因
- **性能优化**: 根据复用率和等待时间调整连接池大小

---

## 🎯 验收标准

### 功能验收
- [ ] 定义标准的 `ConnectionStats` 数据模型
- [ ] 所有连接管理器都能返回标准化的统计信息
- [ ] 实现 `ConnectionMonitor` 类，定期收集并记录状态
- [ ] 集成到 `DataSourceFactory`，提供全局状态查询接口

### 监控指标
- **总连接数**: 当前建立的连接数量
- **活跃连接数**: 正在使用的连接数量
- **空闲连接数**: 可用但未使用的连接数量
- **总创建次数**: 累计创建的连接数
- **总复用次数**: 累计复用的连接数
- **复用率**: 复用次数 / (创建次数 + 复用次数)

---

## 🏗️ 技术设计

### 1. 统计数据模型

```python
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
```

### 2. 监控器实现

```python
class ConnectionMonitor:
    """连接状态监控器"""
    
    def __init__(self):
        self._managers = {}  # source_name -> manager
        
    def register(self, source_name: str, manager: ConnectionManagerInterface):
        self._managers[source_name] = manager
        
    async def get_all_stats(self) -> Dict[str, Any]:
        """获取所有注册管理器的统计信息"""
        stats = {}
        for name, manager in self._managers.items():
            try:
                raw_stats = manager.get_stats()
                # 转换为标准格式
                stats[name] = self._normalize_stats(name, raw_stats)
            except Exception as e:
                stats[name] = {"error": str(e)}
        return stats
```

---

## 📅 实施计划

### 步骤 1: 定义数据模型
在 `src/models/monitor_models.py` 中定义 `ConnectionStats`。

### 步骤 2: 增强 get_stats 实现
确保 `MootdxConnection` 和 `TongDaXinConnectionAdapter` 的 `get_stats` 返回足够的信息以填充模型。

### 步骤 3: 实现监控器
在 `src/core/monitoring/connection_monitor.py` 中实现监控逻辑。

### 步骤 4: 集成
在 `DataSourceFactory` 中集成监控器，自动注册创建的数据源。

---

## 🧪 测试计划

- `test_connection_stats.py`: 验证统计模型序列化
- `test_connection_monitor.py`: 验证监控器收集逻辑

---

**文档版本**: v1.0  
**创建时间**: 2025-11-29  
**预计完成时间**: 2025-11-29
