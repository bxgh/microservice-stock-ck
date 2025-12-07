# 架构迁移指南

## 概述

本指南帮助开发者从旧的分笔数据接口迁移到统一的新架构。

## 迁移时间线

### 已完成的变更
- ✅ 2025-11-25: 删除重复的 `tick_data_routes.py`
- ✅ 2025-11-25: 整合通达信数据源到 FenbiEngine
- ✅ 2025-11-25: 统一API接口到 `/api/v1/fenbi/` 路径
- ✅ 2025-11-25: 实现自动数据源回退机制

### 影响范围
- **API端点**: 分笔数据相关接口
- **数据源**: 通达信和 MooTDX 数据源
- **客户端**: 需要更新API调用路径

## 旧架构 vs 新架构

### 旧架构 (已废弃)
```bash
# 旧的分笔数据接口
GET /api/v1/ticks/{stock_code}           # 单个股票
POST /api/v1/ticks/batch                 # 批量获取
GET /api/v1/ticks/status                 # 状态检查
```

### 新架构 (推荐)
```bash
# 新的统一分笔数据接口
GET /api/v1/fenbi/{symbol}/date/{date}           # 单个股票
GET /api/v1/fenbi/{symbol}/date/{date}/summary    # 数据摘要
GET /api/v1/fenbi/engine/stats                   # 引擎状态
POST /api/v1/fenbi/batch                           # 批量获取
```

## 具体迁移步骤

### 1. API端点迁移

#### 旧: 获取单个股票分笔数据
```python
# 旧代码
import requests
response = requests.get(
    "http://localhost:8088/api/v1/ticks/000001",
    params={
        "trade_date": "2025-11-20",
        "market": "SZ",
        "include_auction": True
    }
)
```

#### 新: 获取单个股票分笔数据
```python
# 新代码
import requests
response = requests.get(
    "http://localhost:8088/api/v1/fenbi/000001/date/20251120",
    params={
        "market": "SZ",
        "enable_time_sort": True,
        "enable_deduplication": True
    }
)
```

### 2. 日期格式变更

#### 旧格式 (ISO日期)
```python
params = {"trade_date": "2025-11-20"}
```

#### 新格式 (YYYYMMDD)
```python
# 直接在路径中
"/api/v1/fenbi/000001/date/20251120"
```

**日期格式转换函数**:
```python
def convert_date_format(date_str):
    """将 ISO 日期转换为 YYYYMMDD 格式"""
    from datetime import datetime
    if isinstance(date_str, str) and '-' in date_str:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y%m%d")
    return date_str
```

### 3. 批量接口迁移

#### 旧: 批量获取
```python
# 旧代码
payload = {
    "stock_codes": ["000001", "000002"],
    "date": "2025-11-20",
    "include_auction": True
}
response = requests.post(
    "http://localhost:8088/api/v1/ticks/batch",
    json=payload
)
```

#### 新: 批量获取
```python
# 新代码
payload = {
    "requests": [
        {"symbol": "000001", "date": "20251120", "market": "SZ"},
        {"symbol": "000002", "date": "20251120", "market": "SZ"}
    ]
}
response = requests.post(
    "http://localhost:8088/api/v1/fenbi/batch",
    json=payload
)
```

### 4. 响应格式变更

#### 旧响应格式
```json
{
  "success": true,
  "data": {
    "stock_code": "000001",
    "tick_data": [...],
    "record_count": 12345
  },
  "message": "数据获取成功"
}
```

#### 新响应格式
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

**响应数据适配器**:
```python
def adapt_response_data(old_response_data):
    """适配旧响应格式到新格式"""
    if 'records' in old_response_data:
        # 新格式，无需适配
        return old_response_data

    if 'tick_data' in old_response_data:
        # 旧格式，需要适配
        return {
            "symbol": old_response_data.get('stock_code'),
            "records": old_response_data.get('tick_data', []),
            "total_count": old_response_data.get('record_count', 0),
            "unique_count": old_response_data.get('record_count', 0),
            "duplicates_removed": 0,
            "processing_stats": {},
            "quality_report": {"basic_quality": {"completeness_score": 0}}
        }

    return old_response_data
```

## 迁移检查清单

### ✅ API调用更新
- [ ] 更新基础URL路径
- [ ] 调整日期格式
- [ ] 更新请求参数名称
- [ ] 处理响应格式变化

### ✅ 功能验证
- [ ] 测试单个股票数据获取
- [ ] 测试批量数据获取
- [ ] 验证错误处理
- [ ] 检查性能表现

### ✅ 代码清理
- [ ] 移除旧API依赖
- [ ] 更新日志和监控
- [ ] 更新文档和注释
- [ ] 清理不再使用的工具函数

## 兼容性处理

### 渐进式迁移策略

#### 1. 双重实现期
```python
class TickDataClient:
    def __init__(self, use_legacy=False):
        self.use_legacy = use_legacy
        self.base_url = "http://localhost:8088/api/v1"

    def get_tick_data(self, symbol, date, market=None):
        if self.use_legacy:
            return self._get_tick_data_legacy(symbol, date, market)
        else:
            return self._get_tick_data_new(symbol, date, market)

    def _get_tick_data_legacy(self, symbol, date, market):
        # 旧API实现
        pass

    def _get_tick_data_new(self, symbol, date, market):
        # 新API实现
        pass
```

#### 2. 配置开关
```python
# config.py
USE_NEW_TICK_API = os.getenv("USE_NEW_TICK_API", "true").lower() == "true"

# client.py
if USE_NEW_TICK_API:
    from .new_client import NewTickDataClient as TickDataClient
else:
    from .legacy_client import LegacyTickDataClient as TickDataClient
```

### 回滚计划

如果新架构出现问题，可以快速回滚：

1. **保留旧代码**: 在独立分支保留旧实现
2. **配置开关**: 使用环境变量控制API版本
3. **监控告警**: 设置新架构的监控和告警
4. **快速切换**: 通过配置快速切换到旧接口

## 测试验证

### 单元测试示例

```python
import pytest
import requests

class TestMigration:
    def test_single_stock_data(self):
        """测试单个股票数据获取"""
        # 测试新接口
        response = requests.get(
            "http://localhost:8088/api/v1/fenbi/000001/date/20251120"
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_batch_data(self):
        """测试批量数据获取"""
        payload = {
            "requests": [
                {"symbol": "000001", "date": "20251120"},
                {"symbol": "000002", "date": "20251120"}
            ]
        }
        response = requests.post(
            "http://localhost:8088/api/v1/fenbi/batch",
            json=payload
        )
        assert response.status_code == 200
        assert len(response.json()["results"]) == 2

    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效股票代码
        response = requests.get(
            "http://localhost:8088/api/v1/fenbi/INVALID/date/20251120"
        )
        # 应该返回空结果或错误，但不应该崩溃
        assert response.status_code == 200
```

### 性能测试

```python
import time
import requests
import concurrent.futures

def benchmark_api_performance():
    """对比新旧API性能"""
    symbols = ["000001", "000002", "600000", "600036", "300001"]
    date = "20251120"

    # 测试新API
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for symbol in symbols:
            future = executor.submit(
                requests.get,
                f"http://localhost:8088/api/v1/fenbi/{symbol}/date/{date}"
            )
            futures.append(future)

        for future in concurrent.futures.as_completed(futures):
            response = future.result()
            print(f"Status: {response.status_code}")

    end_time = time.time()
    print(f"新API耗时: {end_time - start_time:.2f} 秒")

if __name__ == "__main__":
    benchmark_api_performance()
```

## 常见问题和解决方案

### Q1: 新接口返回数据格式不同
**解决方案**: 使用数据适配器函数
```python
def adapt_old_response_to_new(old_data):
    """将旧响应格式适配为新格式"""
    return {
        "success": True,
        "data": {
            "symbol": old_data.get("stock_code"),
            "records": old_data.get("tick_data", []),
            "total_count": old_data.get("record_count", 0)
        }
    }
```

### Q2: 日期格式变更导致问题
**解决方案**: 统一日期处理函数
```python
def standardize_date(date_input):
    """标准化日期格式为YYYYMMDD"""
    if isinstance(date_input, str):
        if '-' in date_input:  # ISO格式
            return date_input.replace('-', '')
        elif len(date_input) == 8:  # 已经是YYYYMMDD
            return date_input
    return date_input
```

### Q3: 请求参数名称变化
**解决方案**: 参数映射表
```python
PARAM_MAPPING = {
    # 旧参数名 -> 新参数名
    "trade_date": None,  # 日期现在在路径中
    "stock_code": "symbol",
    "include_auction": None,  # 新接口自动包含
}

def map_request_params(old_params):
    """映射旧参数到新参数"""
    new_params = {}
    for old_key, value in old_params.items():
        new_key = PARAM_MAPPING.get(old_key, old_key)
        if new_key:
            new_params[new_key] = value
    return new_params
```

## 监控和日志

### 迁移监控指标

1. **API调用统计**
   - 新旧接口调用比例
   - 响应时间对比
   - 错误率对比

2. **数据质量监控**
   - 数据完整性评分
   - 时间覆盖度
   - 去重率

3. **系统健康监控**
   - 数据源连接状态
   - 内存使用情况
   - 并发处理能力

### 日志记录

```python
import logging

logger = logging.getLogger(__name__)

class MigrationLogger:
    @staticmethod
    def log_api_call(api_type, endpoint, params, response_time, success):
        logger.info(f"API调用 - 类型: {api_type}, 端点: {endpoint}, "
                   f"耗时: {response_time:.3f}s, 成功: {success}")

    @staticmethod
    def log_migration_progress(component, status):
        logger.info(f"迁移进度 - 组件: {component}, 状态: {status}")

    @staticmethod
    def log_error(error_type, error_msg, context):
        logger.error(f"迁移错误 - 类型: {error_type}, 消息: {error_msg}, "
                    f"上下文: {context}")
```

## 完成确认

### 迁移完成检查表

- [ ] **代码更新**: 所有客户端代码已更新为新API
- [ ] **测试通过**: 所有功能测试和性能测试通过
- [ ] **文档更新**: API文档和用户指南已更新
- [ ] **监控就绪**: 新接口监控和告警已配置
- [ ] **旧代码清理**: 旧接口相关代码已清理
- [ ] **团队培训**: 开发团队已接受新接口培训

### 上线后验证

1. **功能验证**: 确保所有功能正常工作
2. **性能验证**: 确认性能符合预期
3. **稳定性验证**: 观察24小时稳定性
4. **用户反馈**: 收集并处理用户反馈

## 支持和帮助

### 联系方式
- 技术支持: tech-support@example.com
- 文档地址: https://docs.example.com/api
- 问题反馈: https://github.com/example/issues

### 相关文档
- [API 参考文档](api_reference.md)
- [架构设计文档](unified_tick_data_architecture.md)
- [故障排除指南](troubleshooting.md)

---

**迁移完成后，您将享受到统一架构带来的所有优势：更好的稳定性、更灵活的数据源选择和更简洁的维护体验！**