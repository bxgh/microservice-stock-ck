# Story 002-04: 统一数据源连接接口

**Story ID**: STORY-002-04  
**Epic**: EPIC-002 高可用采集引擎  
**优先级**: P1  
**估算**: 3 天  
**状态**: ✅ 已完成  
**依赖**: Story 2, Story 3  
**实际完成时间**: 2025-11-29

---

## 📋 Story 概述

定义并实现统一的 `ConnectionManagerInterface` 接口，规范化不同数据源（Mootdx, TongDaXin）的连接管理方式。这将消除业务层对特定数据源实现的依赖，降低后续扩展新数据源的复杂度。

### 业务价值
- **降低扩展成本**: 新增数据源只需实现标准接口，无需修改业务逻辑
- **提升可维护性**: 消除业务代码中的 `if/else` 类型判断
- **统一监控**: 为后续的连接池监控（Story 5）提供统一的数据获取入口

---

## 🎯 验收标准

### 功能验收
- [ ] 定义 `ConnectionManagerInterface` 抽象基类
- [ ] `MootdxConnection` 实现该接口，保持现有功能不变
- [ ] `TongDaXinClient` (或其适配器) 实现该接口
- [ ] `DataSourceBase` 更新为使用统一接口
- [ ] 现有数据采集功能在重构后依然正常工作

### 代码质量验收
- [ ] 接口定义清晰，包含类型注解和文档字符串
- [ ] 单元测试覆盖接口的所有实现
- [ ] 通过静态类型检查 (mypy)

---

## 🏗️ 技术设计

### 1. 接口定义

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class ConnectionManagerInterface(ABC):
    """统一的连接管理接口"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化连接管理器（建立连接/连接池）"""
        pass
    
    @abstractmethod
    async def get_connection(self) -> Any:
        """获取一个可用连接"""
        pass
    
    @abstractmethod
    async def release_connection(self, connection: Any):
        """释放连接（对于池化连接是归还，对于单连接可能不操作）"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理所有资源（关闭所有连接）"""
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """检查管理器健康状态"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        pass
```

### 2. 适配器模式

由于 `TongDaXinClient` 已经是一个复杂的类，我们可能需要使用适配器模式来适配接口，而不是直接修改它，以减少风险。

```python
class TongDaXinConnectionManager(ConnectionManagerInterface):
    """TongDaXinClient 的适配器"""
    
    def __init__(self, client: TongDaXinClient):
        self.client = client
        
    async def initialize(self) -> bool:
        return await self.client.initialize()
        
    # ... 实现其他方法
```

对于 `MootdxConnection`，由于它是我们自己控制的较小类，可以直接修改它实现接口。

### 3. 集成点

在 `DataSourceBase` 中，我们将不再直接依赖具体类，而是依赖接口：

```python
class DataSourceBase(ABC):
    def __init__(self):
        self.connection_manager: ConnectionManagerInterface = None
        
    async def connect(self) -> bool:
        return await self.connection_manager.initialize()
```

---

## 📅 实施计划

### Day 1: 接口定义与 Mootdx 适配
1. 创建 `src/core/interfaces.py` 定义接口
2. 修改 `MootdxConnection` 实现接口
3. 编写单元测试验证 Mootdx 实现

### Day 2: TongDaXin 适配
1. 创建 `TongDaXinConnectionAdapter`
2. 适配 `TongDaXinClient` 的现有方法
3. 编写单元测试验证适配器

### Day 3: 集成与验证
1. 更新 `DataSourceBase` 和子类
2. 运行所有集成测试
3. 验证业务流程（SnapshotRecorder）

---

## ⚠️ 风险与应对

### 风险 1: 破坏现有功能
**应对**: 保持向后兼容性。在 `MootdxConnection` 中保留旧方法（标记为 deprecated），直到所有调用方都更新。

### 风险 2: TongDaXin 连接池逻辑复杂
**应对**: 使用适配器模式，只包装必要的调用，不修改 `TongDaXinClient` 内部复杂的池化逻辑。

---

## 🧪 测试计划

### 单元测试
- `test_mootdx_connection_manager.py`: 验证 Mootdx 实现符合接口规范
- `test_tongdaxin_connection_adapter.py`: 验证适配器正确转发调用

### 集成测试
- `test_unified_interface_integration.py`: 验证通过统一接口能正常获取数据

---

**文档版本**: v1.0  
**创建时间**: 2025-11-29  
**预计完成时间**: 2025-12-02
