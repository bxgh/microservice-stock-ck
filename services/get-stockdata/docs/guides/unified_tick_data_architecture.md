# 统一分笔数据架构文档

## 概述

本文档描述了 get-stockdata 微服务中统一分笔数据获取架构的设计和实现。

## 架构目标

- **统一接口** - 提供单一入口获取分笔数据，支持多种数据源
- **高可用性** - 自动故障转移和数据源回退机制
- **可扩展性** - 易于添加新的数据源
- **向后兼容** - 保持现有API接口不变

## 架构组件

### 1. 数据源层 (Data Sources)

#### 1.1 基础接口
```python
# src/data_sources/base.py
class DataSourceBase(ABC):
    """数据源基类，定义统一接口"""

    @abstractmethod
    async def connect(self) -> bool: pass

    @abstractmethod
    async def get_tick_data(self, request: TickDataRequest) -> List[TickData]: pass

    @abstractmethod
    async def get_tick_data_dataframe(self, request: TickDataRequest) -> pd.DataFrame: pass

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]: pass

    @abstractmethod
    async def close(self): pass
```

#### 1.2 数据源实现

##### 通达信数据源 (TongDaXinDataSource)
- **文件**: `src/data_sources/tongdaxin/fetcher.py`
- **优先级**: 默认数据源
- **特点**:
  - 基于现有 `tongdaxin_client`
  - 支持实时行情数据
  - 稳定性高

##### MooTDX数据源 (MootdxDataSource)
- **文件**: `src/data_sources/mootdx/fetcher.py`
- **优先级**: 备用数据源
- **特点**:
  - 开源通达信协议实现
  - 丰富的数据获取功能
  - 作为通达信失败的备用

#### 1.3 数据源工厂
```python
# src/data_sources/factory.py
class DataSourceFactory:
    """数据源工厂，统一管理所有数据源"""

    @staticmethod
    def create_source(source_type: str, config: Optional[Dict[str, Any]] = None) -> DataSourceBase:
        """创建指定类型的数据源"""
        pass

    @staticmethod
    def create_default_source() -> DataSourceBase:
        """创建默认数据源"""
        pass

    @staticmethod
    def get_available_sources() -> List[str]:
        """获取可用数据源列表"""
        pass
```

### 2. 引擎层 (Engine Layer)

#### 2.1 Fenbi引擎
```python
# src/services/fenbi_engine.py
class FenbiEngine:
    """分笔数据获取引擎"""

    def __init__(self, source_type: str = "tongdaxin", config: Optional[dict] = None):
        """初始化引擎，支持多种数据源"""
        self.data_source = DataSourceFactory.create_source(source_type, config)

    async def get_tick_data(self, symbol: str, date: str, **kwargs) -> List:
        """获取分笔数据，支持时间排序和去重"""
        pass

    def generate_enhanced_report(self, data: List) -> dict:
        """生成数据质量报告"""
        pass
```

#### 2.2 核心组件

- **TimeFormatter**: 时间格式化和排序
- **DataDeduplicator**: 数据去重处理
- **StatisticsGenerator**: 统计分析生成

### 3. 接口层 (API Layer)

#### 3.1 REST API接口

| 端点 | 方法 | 描述 | 示例 |
|------|------|------|------|
| `/api/v1/fenbi/{symbol}/date/{date}` | GET | 获取股票分笔数据 | `/api/v1/fenbi/000001/date/20251120` |
| `/api/v1/fenbi/{symbol}/date/{date}/summary` | GET | 获取数据摘要 | `/api/v1/fenbi/000001/date/20251120/summary` |
| `/api/v1/fenbi/engine/stats` | GET | 获取引擎状态 | `/api/v1/fenbi/engine/stats` |
| `/api/v1/fenbi/batch` | POST | 批量获取数据 | `/api/v1/fenbi/batch` |

#### 3.2 API响应格式

```json
{
  "success": true,
  "message": "获取股票 000001 分笔数据成功",
  "data": {
    "symbol": "000001",
    "date": "20251120",
    "market": "SZ",
    "records": [...],
    "total_count": 12345,
    "unique_count": 12345,
    "duplicates_removed": 0,
    "processing_stats": {...},
    "quality_report": {...}
  }
}
```

### 4. 命令行接口 (CLI)

#### 4.1 Fenbi CLI
```bash
# 基本用法
python -m services.fenbi_cli --symbol 000001 --date 20251120

# 完整参数
python -m services.fenbi_cli \
  --symbol 000001 \
  --date 20251120 \
  --format both \
  --debug
```

## 数据源配置

### 默认配置
```python
# src/data_sources/factory.py
DATA_SOURCE_CONFIG = {
    "tongdaxin": {
        "class": TongDaXinDataSource,
        "default": False,  # 优先作为默认
        "timeout": 30,
        "max_connections": 5
    },
    "mootdx": {
        "class": MootdxDataSource,
        "default": True,   # 作为备用
        "timeout": 60,
        "best_ip": True,
        "overlap_ratio": 0.2,
        "batch_size": 800,
        "max_records": 200000,
        "max_consecutive_empty": 5
    }
}
```

### 数据源选择策略

1. **默认优先级**: tongdaxin > mootdx
2. **自动回退**: tongdaxin失败时自动切换到mootdx
3. **手动指定**: 可以通过API指定使用特定数据源

## 故障处理机制

### 1. 连接失败处理
```python
# src/api/fenbi_routes.py
async def get_fenbi_engine():
    """智能数据源选择"""
    try:
        fenbi_engine = FenbiEngine("tongdaxin")  # 优先通达信
        await fenbi_engine.data_source.connect()
    except Exception as e:
        logger.error(f"通达信数据源失败: {e}")
        try:
            fenbi_engine = FenbiEngine("mootdx")  # 回退到mootdx
            await fenbi_engine.data_source.connect()
            logger.info("使用mootdx数据源作为备用")
        except Exception as e2:
            logger.error(f"所有数据源都失败: {e2}")
            raise HTTPException(status_code=500, detail="服务初始化失败")
```

### 2. 数据获取失败处理
- **重试机制**: 内置指数退避重试
- **错误报告**: 详细的错误信息和建议
- **部分成功**: 即使部分数据获取失败，也返回可用的数据

## 性能优化

### 1. 数据处理优化
- **批量处理**: 支持批量获取多只股票数据
- **内存管理**: 大数据集的流式处理
- **缓存机制**: 连接池和结果缓存

### 2. 网络优化
- **连接复用**: HTTP连接池
- **并发控制**: 限制同时进行的数据获取请求数
- **超时控制**: 合理的网络超时设置

## 监控和日志

### 1. 健康检查
- **服务状态**: `/api/v1/health`
- **数据源状态**: `/api/v1/fenbi/engine/stats`
- **内部接口**: `/internal/fenbi/health`

### 2. 日志记录
```python
# 日志级别
logger.info("数据获取开始")
logger.warning("数据源连接失败，尝试备用数据源")
logger.error("所有数据源都不可用")

# 关键指标
- 数据获取耗时
- 成功/失败率
- 数据质量评分
- 连接池状态
```

## 扩展指南

### 添加新数据源

1. **创建数据源类**
```python
# src/data_sources/new_source/fetcher.py
class NewDataSource(DataSourceBase):
    """新数据源实现"""

    def __init__(self, **kwargs):
        # 初始化配置
        pass

    async def connect(self) -> bool:
        # 实现连接逻辑
        pass

    async def get_tick_data(self, request: TickDataRequest) -> List[TickData]:
        # 实现数据获取逻辑
        pass
```

2. **更新工厂配置**
```python
# src/data_sources/factory.py
from .new_source.fetcher import NewDataSource

DATA_SOURCE_CONFIG["new_source"] = {
    "class": NewDataSource,
    "default": False,
    # 添加配置参数
}
```

3. **测试集成**
- 添加单元测试
- 验证API接口
- 测试故障转移

## 最佳实践

### 1. API使用
- **参数验证**: 使用有效的股票代码和日期格式
- **错误处理**: 检查响应中的 `success` 字段
- **分页处理**: 大数据量时使用分页或流式处理

### 2. 数据质量
- **验证数据完整性**: 检查时间覆盖和记录数量
- **处理重复数据**: 利用内置的去重功能
- **监控数据质量**: 使用质量报告评估数据可靠性

### 3. 性能考虑
- **合理设置超时**: 避免长时间等待
- **使用缓存**: 对于重复请求使用缓存
- **批量操作**: 多股票请求使用批量接口

## 故障排除

### 常见问题

1. **数据源连接失败**
   - 检查网络连接
   - 验证数据源服务状态
   - 尝试切换到备用数据源

2. **数据获取不完整**
   - 检查请求参数是否正确
   - 验证股票代码和日期格式
   - 查看数据质量报告

3. **性能问题**
   - 监控API响应时间
   - 检查数据源负载情况
   - 考虑使用批量接口

### 调试技巧

```python
# 启用调试模式
python -m services.fenbi_cli --symbol 000001 --date 20251120 --debug

# 查看详细日志
docker logs get-stockdata-test

# 测试API端点
curl -X GET "http://localhost:8088/api/v1/fenbi/engine/stats"
```

## 版本历史

- **v1.0**: 基础分笔数据获取功能
- **v2.0**: 统一架构，支持多数据源
- **v2.1**: 增加通达信数据源支持
- **v2.2**: 优化故障转移机制

## 总结

统一分笔数据架构通过抽象接口层和工厂模式，实现了：
- **代码复用**: 避免重复实现相似功能
- **灵活配置**: 支持动态切换数据源
- **高可用性**: 多重保障确保服务稳定性
- **易于维护**: 模块化设计便于扩展和维护

该架构为未来的功能扩展和数据源集成提供了坚实的基础。