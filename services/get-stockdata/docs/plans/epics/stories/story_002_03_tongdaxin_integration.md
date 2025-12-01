# Story 002-03: 修复 TongDaXin 数据源集成

**Story ID**: STORY-002-03  
**Epic**: EPIC-002 高可用采集引擎  
**优先级**: P1  
**估算**: 1 天  
**状态**: ✅ 已完成  
**依赖**: 无  
**实际完成时间**: 2025-11-29

---

## 📋 Story 概述

修复 `TongDaXinDataSource` 的集成问题，使其能够通过 `DataSourceFactory` 正常创建和使用，充分利用现有的连接池功能。

### 业务价值
- 启用备用数据源，提升系统容错能力
- 利用现有的连接池实现，提升性能
- 为多数据源切换奠定基础

---

## 🎯 验收标准

### 功能验收
- [ ] 能通过 `DataSourceFactory.create('tongdaxin')` 创建实例
- [ ] 能正常连接 TongDaXin 服务器
- [ ] 能正常获取分笔数据
- [ ] 现有 `TongDaXinClient` 连接池功能不受影响
- [ ] 与 `MootdxDataSource` 接口保持一致

### 测试验收
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试验证数据获取功能
- [ ] 连接池功能测试通过

---

## 🔍 现状分析

### 当前问题

**文件**: `src/data_sources/factory.py`

```python
# Line 12 - 导入被注释
# from .tongdaxin.fetcher import TongDaXinDataSource  # 暂时注释掉，缺少依赖模块

# Line 27 - 数据源配置被禁用
"tongdaxin": {
    "class": None,  # TongDaXinDataSource,  # 暂时禁用，缺少依赖模块
    "default": False,
}
```

### 可能的原因

1. **缺少依赖**: `pytdx` 库未安装或版本不兼容
2. **导入路径错误**: 模块路径可能有问题
3. **循环依赖**: 可能存在模块间的循环引用
4. **代码不完整**: TongDaXinDataSource 实现可能不完整

---

## 🏗️ 实施计划

### 阶段 1: 诊断问题 (2小时)

#### 步骤 1.1: 检查文件结构
```bash
# 查看 TongDaXin 相关文件
find src/data_sources/tongdaxin -type f -name "*.py"
```

#### 步骤 1.2: 尝试导入
```bash
# 测试导入
cd /home/bxgh/microservice-stock/services/get-stockdata
docker compose -f docker-compose.dev.yml run --rm get-stockdata \
  python3 -c "from src.data_sources.tongdaxin.fetcher import TongDaXinDataSource"
```

#### 步骤 1.3: 检查依赖
```bash
# 检查 pytdx 是否安装
docker compose -f docker-compose.dev.yml run --rm get-stockdata \
  python3 -c "import pytdx; print(pytdx.__version__)"
```

#### 步骤 1.4: 查看错误信息
记录具体的错误堆栈，确定根本原因。

---

### 阶段 2: 修复问题 (4小时)

#### 场景 A: 缺少依赖

**解决方案**:
1. 在 `requirements.txt` 中添加 `pytdx`
2. 重新构建 Docker 镜像

```txt
# requirements.txt
pytdx>=1.72
```

#### 场景 B: 导入路径问题

**解决方案**:
1. 检查 `__init__.py` 文件是否存在
2. 修正导入路径

```python
# src/data_sources/tongdaxin/__init__.py
from .fetcher import TongDaXinDataSource

__all__ = ['TongDaXinDataSource']
```

#### 场景 C: 代码不完整

**解决方案**:
1. 查看 `TongDaXinDataSource` 实现
2. 补充缺失的方法
3. 确保实现 `DataSourceBase` 接口

---

### 阶段 3: 集成测试 (2小时)

#### 测试 1: 工厂创建测试
```python
from src.data_sources.factory import DataSourceFactory

# 测试创建
source = DataSourceFactory.create('tongdaxin')
assert source is not None
assert source.source_name == 'tongdaxin'
```

#### 测试 2: 连接测试
```python
# 测试连接
success = await source.connect()
assert success == True
```

#### 测试 3: 数据获取测试
```python
from src.models.tick_models import TickDataRequest
from datetime import datetime

# 测试获取数据
request = TickDataRequest(
    stock_code='000001',
    date=datetime(2025, 11, 29)
)
data = await source.get_tick_data(request)
assert len(data) > 0
```

---

## 💻 代码修改

### 1. 取消注释 factory.py

**文件**: `src/data_sources/factory.py`

```python
# 修改前
# from .tongdaxin.fetcher import TongDaXinDataSource  # 暂时注释掉，缺少依赖模块

# 修改后
from .tongdaxin.fetcher import TongDaXinDataSource
```

```python
# 修改前
"tongdaxin": {
    "class": None,  # TongDaXinDataSource,  # 暂时禁用，缺少依赖模块
    "default": False,
}

# 修改后
"tongdaxin": {
    "class": TongDaXinDataSource,
    "default": False,
}
```

### 2. 确保 TongDaXinDataSource 实现完整

**文件**: `src/data_sources/tongdaxin/fetcher.py`

需要确保实现以下接口：

```python
class TongDaXinDataSource(DataSourceBase):
    @property
    def source_name(self) -> str:
        return "tongdaxin"
    
    @property
    def is_connected(self) -> bool:
        # 实现连接状态检查
        pass
    
    async def connect(self) -> bool:
        # 实现连接逻辑
        pass
    
    async def get_tick_data(self, request: TickDataRequest) -> List[TickData]:
        # 实现数据获取
        pass
    
    async def get_status(self) -> Dict[str, Any]:
        # 实现状态查询
        pass
    
    async def close(self):
        # 实现资源清理
        pass
```

### 3. 添加依赖（如需要）

**文件**: `requirements.txt`

```txt
# 如果缺少 pytdx
pytdx>=1.72
```

---

## 🧪 测试计划

### 单元测试

**文件**: `tests/test_tongdaxin_integration.py`

```python
import pytest
from src.data_sources.factory import DataSourceFactory
from src.models.tick_models import TickDataRequest
from datetime import datetime

class TestTongDaXinIntegration:
    """TongDaXin 数据源集成测试"""
    
    def test_factory_can_create_tongdaxin(self):
        """测试工厂能创建 TongDaXin 数据源"""
        source = DataSourceFactory.create('tongdaxin')
        assert source is not None
        assert source.source_name == 'tongdaxin'
    
    @pytest.mark.asyncio
    async def test_tongdaxin_can_connect(self):
        """测试 TongDaXin 能连接"""
        source = DataSourceFactory.create('tongdaxin')
        success = await source.connect()
        assert success == True
        assert source.is_connected == True
    
    @pytest.mark.asyncio
    async def test_tongdaxin_can_fetch_data(self):
        """测试 TongDaXin 能获取数据"""
        source = DataSourceFactory.create('tongdaxin')
        await source.connect()
        
        request = TickDataRequest(
            stock_code='000001',
            date=datetime(2025, 11, 29)
        )
        
        data = await source.get_tick_data(request)
        assert isinstance(data, list)
        # 注意：可能返回空列表（非交易日）
    
    @pytest.mark.asyncio
    async def test_tongdaxin_connection_pool(self):
        """测试 TongDaXin 连接池功能"""
        source = DataSourceFactory.create('tongdaxin')
        await source.connect()
        
        # 获取连接池状态
        status = await source.get_status()
        assert 'connection_pool' in status or 'client' in status
    
    @pytest.mark.asyncio
    async def test_tongdaxin_cleanup(self):
        """测试 TongDaXin 资源清理"""
        source = DataSourceFactory.create('tongdaxin')
        await source.connect()
        await source.close()
        
        # 验证连接已关闭
        assert source.is_connected == False
```

---

## 📊 风险评估

### 风险 1: 依赖版本不兼容
**概率**: 中  
**影响**: 高  
**应对**: 
- 测试多个 pytdx 版本
- 如果不兼容，考虑降级或升级 Python 版本

### 风险 2: TongDaXin 服务器不稳定
**概率**: 低  
**影响**: 中  
**应对**:
- 添加重试机制（利用 Story 1 的 ResilientClient）
- 设置合理的超时时间

### 风险 3: 代码实现不完整
**概率**: 中  
**影响**: 高  
**应对**:
- 如果缺失关键功能，参考 MootdxDataSource 实现
- 如果工作量过大，考虑暂时放弃该数据源

---

## 🎯 成功标准

### 最小可行标准 (MVP)
- ✅ 能通过工厂创建实例
- ✅ 能成功连接
- ✅ 能获取数据（即使是空数据）

### 理想标准
- ✅ 连接池功能正常
- ✅ 性能与 Mootdx 相当
- ✅ 测试覆盖率 > 80%
- ✅ 文档完整

---

## 📝 决策点

### 决策 1: 是否值得修复？

**评估标准**:
- 修复时间 < 1 天 → 继续
- 修复时间 > 1 天 → 评估是否放弃

**放弃条件**:
- 依赖问题无法解决
- 代码实现严重不完整（需要重写）
- TongDaXin 服务不可用

### 决策 2: 如果放弃，后续计划？

**替代方案**:
- 专注于优化 Mootdx 数据源
- 考虑集成其他数据源（如 AkShare）
- 将 TongDaXin 标记为"已废弃"

---

## ✅ 完成检查清单

### 诊断阶段
- [ ] 检查文件结构完整性
- [ ] 尝试导入并记录错误
- [ ] 检查依赖是否安装
- [ ] 确定根本原因

### 修复阶段
- [ ] 修复依赖问题（如有）
- [ ] 修复导入路径（如有）
- [ ] 补充缺失代码（如有）
- [ ] 取消 factory.py 中的注释

### 测试阶段
- [ ] 工厂创建测试通过
- [ ] 连接测试通过
- [ ] 数据获取测试通过
- [ ] 连接池测试通过
- [ ] 单元测试覆盖率 > 80%

### 文档阶段
- [ ] 更新使用文档
- [ ] 记录已知问题
- [ ] 生成实施报告

---

## 📚 相关文档

- TongDaXin Client 实现: `src/services/tongdaxin_client.py`
- 数据源工厂: `src/data_sources/factory.py`
- 基类定义: `src/data_sources/base.py`

---

**文档版本**: v1.0  
**创建时间**: 2025-11-29  
**预计完成时间**: 2025-11-30
