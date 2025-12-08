# 新增 Data Service 开发指南

本文档指导开发者如何在 `get-stockdata` 微服务中添加新的数据服务。

## 架构概览

系统采用分层架构：
1. **API Layer** (`src/api/`): HTTP接口
2. **Service Layer** (`src/data_services/`): 业务逻辑封装
3. **Manager Layer** (`DataServiceManager`): 数据源调度与容错
4. **Provider Layer** (`src/data_sources/providers/`): 具体数据源实现

## 开发步骤

### Step 1: 定义数据类型
在 `src/data_sources/providers/base.py` 的 `DataType` 枚举中添加新类型。

```python
class DataType(Enum):
    # ... 现有类型
    NEW_FEATURE = "new_feature"  # 新增类型
```

### Step 2: 实现数据获取逻辑
选择合适的数据源 Provider (如 `AkshareProvider`)，实现数据获取方法，并在 `__init__` 中注册能力。

文件: `src/data_sources/providers/akshare_provider.py`

```python
class AkshareProvider(DataProvider):
    def __init__(self):
        super().__init__("akshare")
        self.capabilities = [
            # ... 现有能力
            DataType.NEW_FEATURE,  # 注册新能力
        ]
        
    async def get_new_feature_data(self, **kwargs) -> DataResult:
        """实现具体数据获取逻辑"""
        try:
            # 调用 akshare 接口 (注意使用 asyncio.to_thread 避免阻塞)
            df = await asyncio.to_thread(ak.some_api_function, **kwargs)
            return DataResult(success=True, data=df)
        except Exception as e:
            return DataResult(success=False, error=str(e))
            
    async def fetch(self, data_type: DataType, **kwargs) -> DataResult:
        # 分发请求
        if data_type == DataType.NEW_FEATURE:
            return await self.get_new_feature_data(**kwargs)
        # ...
```

### Step 3: 更新 DataServiceManager
在管理器中暴露统一的调用接口。

文件: `src/data_sources/providers/manager.py`

```python
class DataServiceManager:
    # ...
    
    async def get_new_feature(self, param1: str, **kwargs) -> DataResult:
        """获取新特性数据"""
        # 获取对应的 ProviderChain
        chain = self._chains.get(DataType.NEW_FEATURE)
        if not chain:
            return DataResult(success=False, error="No provider for NEW_FEATURE")
        
        # 通过责任链获取数据 (自动处理缓存、降级、重试)
        return await chain.fetch(param1=param1, **kwargs)
```

### Step 4: 创建业务服务类
封装业务逻辑，如参数校验、结果转换等。

文件: `src/data_services/new_feature_service.py`

```python
from src.data_sources.providers.manager import get_data_service

class NewFeatureService:
    async def initialize(self):
        self.data_manager = await get_data_service()
        
    async def get_data(self, code: str):
        # 调用 Manager
        result = await self.data_manager.get_new_feature(code=code)
        
        if not result.success:
            # 处理错误或返回默认值
            return {}
            
        # 业务处理...
        return result.data
        
    async def close(self):
        pass
```

### Step 5: 注册 API 路由
创建路由并注册到应用。

文件: `src/api/routers/new_feature.py`

```python
from fastapi import APIRouter, Depends
from src.data_services.new_feature_service import NewFeatureService

router = APIRouter(prefix="/new-feature", tags=["新特性"])

async def get_service():
    service = NewFeatureService()
    await service.initialize()
    try:
        yield service
    finally:
        await service.close()

@router.get("/{code}")
async def get_feature(code: str, service: NewFeatureService = Depends(get_service)):
    return await service.get_data(code)
```

最后在 `src/main.py` 中 include 这个 router。

### Step 6: 编写测试
在 `tests/data_services/` 下创建测试文件，验证功能。

```python
@pytest.mark.asyncio
async def test_new_feature_service():
    service = NewFeatureService()
    await service.initialize()
    data = await service.get_data("000001")
    assert data is not None
    await service.close()
```

---
**提示**: 尽量复用现有的 `AkshareProvider` 或 `MootdxProvider`，避免创建过多的 Provider 类，除非引入了全新的数据源 SDK。
