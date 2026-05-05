# [DEPRECATED] API 参考文档

⚠️ **注意**: 本文档已过时，请参考最新的功能与数据源文档。

➡️ **最新文档**: [Data Services功能与数据源映射表](../api/services_datasources_features.md)

---
(Old content removed to avoid confusion)

## 概述

本文档详细描述了 get-stockdata 微服务的 REST API 接口。

## 基础信息

- **Base URL**: `http://localhost:8088`
- **API版本**: `v1`
- **内容类型**: `application/json`
- **字符编码**: `UTF-8`

## 通用响应格式

### 成功响应
```json
{
  "success": true,
  "message": "操作成功",
  "data": {
    // 具体数据内容
  },
  "timestamp": "2025-11-25T11:45:01.192696"
}
```

### 错误响应
```json
{
  "success": false,
  "message": "错误描述",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-11-25T11:45:01.192696"
}
```

## 健康检查接口

### GET `/api/v1/health`

获取服务健康状态。

**响应示例**:
```json
{
  "success": true,
  "message": "Service health check completed",
  "data": {
    "status": "healthy",
    "timestamp": "2025-11-25T11:44:57.960649",
    "version": "1.0.0",
    "uptime": 13,
    "checks": {
      "framework": {
        "status": "pass",
        "message": "FastAPI framework is running"
      },
      "api": {
        "status": "pass",
        "message": "API endpoints are accessible"
      },
      "service_registry": {
        "status": "pass",
        "message": "Service registry is available"
      }
    }
  }
}
```

## 分笔数据接口

### 1. 获取股票分笔数据

#### GET `/api/v1/fenbi/{symbol}/date/{date}`

获取指定股票在特定日期的分笔交易数据。

**路径参数**:
- `symbol` (string, required): 股票代码，如 "000001"
- `date` (string, required): 交易日期，格式 "YYYYMMDD"，如 "20251120"

**查询参数**:
- `market` (string, optional): 市场代码，可选值: "SH", "SZ", "BJ"
- `enable_time_sort` (boolean, optional): 是否启用时间排序，默认: true
- `enable_deduplication` (boolean, optional): 是否启用数据去重，默认: true

**请求示例**:
```bash
GET /api/v1/fenbi/000001/date/20251120
GET /api/v1/fenbi/000001/date/20251120?market=SZ&enable_time_sort=true
```

**响应示例**:
```json
{
  "success": true,
  "message": "获取股票 000001 分笔数据成功",
  "data": {
    "symbol": "000001",
    "date": "20251120",
    "market": "SZ",
    "records": [
      {
        "time": "09:30:00",
        "price": 10.50,
        "volume": 1000,
        "amount": 10500.00,
        "direction": "B",
        "code": "000001",
        "date": "20251120"
      }
      // ... 更多记录
    ],
    "total_count": 12345,
    "unique_count": 12345,
    "duplicates_removed": 0,
    "processing_stats": {
      "start_time": "2025-11-25T11:45:01.192696",
      "end_time": "2025-11-25T11:45:03.456789",
      "total_records": 12345,
      "unique_records": 12345,
      "duplicates_removed": 0,
      "success": true,
      "error_message": null,
      "duration": 2.264
    },
    "quality_report": {
      "basic_quality": {
        "completeness_score": 95,
        "time_coverage": 0.98,
        "quality_grade": "A"
      },
      "statistical_analysis": {
        "price": {
          "mean": 10.52,
          "std": 0.15,
          "min": 10.30,
          "max": 10.80
        },
        "volume": {
          "mean": 850,
          "std": 320,
          "min": 100,
          "max": 5000
        }
      },
      "data_characteristics": {
        "time_span": {
          "start_time": "09:30:00",
          "end_time": "15:00:00",
          "total_records": 12345
        }
      }
    }
  }
}
```

### 2. 获取分笔数据摘要

#### GET `/api/v1/fenbi/{symbol}/date/{date}/summary`

获取分笔数据的统计摘要信息，不包含详细记录。

**路径参数**: 同获取分笔数据接口

**查询参数**: 同获取分笔数据接口

**请求示例**:
```bash
GET /api/v1/fenbi/000001/date/20251120/summary
```

**响应示例**:
```json
{
  "success": true,
  "message": "获取股票 000001 分笔数据摘要成功",
  "data": {
    "symbol": "000001",
    "date": "20251120",
    "market": "SZ",
    "record_count": 12345,
    "unique_count": 12345,
    "duplicates_removed": 0,
    "processing_time": 2.264,
    "quality_score": 95,
    "quality_grade": "A",
    "time_coverage": 0.98
  }
}
```

### 3. 获取引擎状态

#### GET `/api/v1/fenbi/engine/stats`

获取Fenbi引擎和当前数据源的状态信息。

**请求示例**:
```bash
GET /api/v1/fenbi/engine/stats
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "engine_stats": {
      "start_time": "2025-11-25T11:45:01.192696",
      "end_time": null,
      "total_records": 12345,
      "unique_records": 12345,
      "duplicates_removed": 0,
      "success": true,
      "error_message": null,
      "duration": 2.264
    },
    "data_source": {
      "name": "tongdaxin",
      "connected": true,
      "type": "TongDaXinDataSource",
      "available_servers": 3,
      "response_time": 50,
      "error_message": null,
      "is_connected": true,
      "timestamp": "2025-11-25T11:45:01.192696"
    }
  }
}
```

### 4. 批量获取分笔数据

#### POST `/api/v1/fenbi/batch`

批量获取多只股票的分笔数据。

**请求体**:
```json
{
  "requests": [
    {
      "symbol": "000001",
      "date": "20251120",
      "market": "SZ"
    },
    {
      "symbol": "000002",
      "date": "20251120",
      "market": "SZ"
    }
    // ... 更多请求
  ]
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "批量获取Fenbi分笔数据完成",
  "results": [
    {
      "symbol": "000001",
      "success": true,
      "record_count": 12345,
      "unique_count": 12345,
      "processing_time": 2.1
    },
    {
      "symbol": "000002",
      "success": true,
      "record_count": 9876,
      "unique_count": 9876,
      "processing_time": 1.8
    }
  ]
}
```

## 内部接口

### 1. 测试Fenbi引擎

#### POST `/internal/fenbi/test`

测试Fenbi引擎连接和基本功能。

**请求示例**:
```bash
POST /internal/fenbi/test
```

**响应示例**:
```json
{
  "success": true,
  "message": "Fenbi引擎测试成功",
  "test_data": {
    "symbol": "000001",
    "date": "20251120",
    "records_count": 12345,
    "engine_stats": {
      "success": true,
      "duration": 2.1
    }
  }
}
```

### 2. 重置Fenbi引擎

#### POST `/internal/fenbi/reset`

重置Fenbi引擎，清除所有缓存和状态。

**请求示例**:
```bash
POST /internal/fenbi/reset
```

**响应示例**:
```json
{
  "success": true,
  "message": "Fenbi引擎重置成功"
}
```

## 错误码说明

| 错误码 | HTTP状态码 | 描述 |
|--------|------------|------|
| `INVALID_SYMBOL` | 400 | 无效的股票代码 |
| `INVALID_DATE` | 400 | 无效的日期格式 |
| `DATA_SOURCE_ERROR` | 500 | 数据源连接失败 |
| `DATA_NOT_FOUND` | 404 | 未找到指定数据 |
| `PROCESSING_ERROR` | 500 | 数据处理错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务暂时不可用 |

## 使用示例

### Python示例

```python
import requests
import json

# 基础URL
BASE_URL = "http://localhost:8088/api/v1"

def get_tick_data(symbol, date, market=None):
    """获取分笔数据"""
    url = f"{BASE_URL}/fenbi/{symbol}/date/{date}"
    params = {}
    if market:
        params['market'] = market

    response = requests.get(url, params=params)
    return response.json()

def get_tick_summary(symbol, date):
    """获取分笔数据摘要"""
    url = f"{BASE_URL}/fenbi/{symbol}/date/{date}/summary"
    response = requests.get(url)
    return response.json()

def batch_get_tick_data(requests):
    """批量获取分笔数据"""
    url = f"{BASE_URL}/fenbi/batch"
    payload = {"requests": requests}
    response = requests.post(url, json=payload)
    return response.json()

# 使用示例
if __name__ == "__main__":
    # 获取平安银行分笔数据
    result = get_tick_data("000001", "20251120", "SZ")
    print(f"获取到 {result['data']['total_count']} 条记录")

    # 获取摘要
    summary = get_tick_summary("000001", "20251120")
    print(f"数据质量评分: {summary['data']['quality_score']}")

    # 批量获取
    batch_requests = [
        {"symbol": "000001", "date": "20251120", "market": "SZ"},
        {"symbol": "000002", "date": "20251120", "market": "SZ"}
    ]
    batch_result = batch_get_tick_data(batch_requests)
    print(f"批量处理完成: {len(batch_result['results'])} 只股票")
```

### JavaScript示例

```javascript
const BASE_URL = "http://localhost:8088/api/v1";

async function getTickData(symbol, date, market = null) {
  const url = new URL(`${BASE_URL}/fenbi/${symbol}/date/${date}`);
  if (market) {
    url.searchParams.append('market', market);
  }

  const response = await fetch(url);
  return await response.json();
}

async function getTickSummary(symbol, date) {
  const response = await fetch(`${BASE_URL}/fenbi/${symbol}/date/${date}/summary`);
  return await response.json();
}

async function batchGetTickData(requests) {
  const response = await fetch(`${BASE_URL}/fenbi/batch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ requests })
  });
  return await response.json();
}

// 使用示例
(async () => {
  try {
    const data = await getTickData('000001', '20251120', 'SZ');
    console.log(`获取到 ${data.data.total_count} 条记录`);

    const summary = await getTickSummary('000001', '20251120');
    console.log(`数据质量评分: ${summary.data.quality_score}`);

    const batchRequests = [
      { symbol: '000001', date: '20251120', market: 'SZ' },
      { symbol: '000002', date: '20251120', market: 'SZ' }
    ];
    const batchResult = await batchGetTickData(batchRequests);
    console.log(`批量处理完成: ${batchResult.results.length} 只股票`);
  } catch (error) {
    console.error('API调用失败:', error);
  }
})();
```

### cURL示例

```bash
# 健康检查
curl -X GET "http://localhost:8088/api/v1/health"

# 获取分笔数据
curl -X GET "http://localhost:8088/api/v1/fenbi/000001/date/20251120?market=SZ"

# 获取数据摘要
curl -X GET "http://localhost:8088/api/v1/fenbi/000001/date/20251120/summary"

# 获取引擎状态
curl -X GET "http://localhost:8088/api/v1/fenbi/engine/stats"

# 批量获取
curl -X POST "http://localhost:8088/api/v1/fenbi/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {"symbol": "000001", "date": "20251120", "market": "SZ"},
      {"symbol": "000002", "date": "20251120", "market": "SZ"}
    ]
  }'
```

## 性能考虑

### 请求限制
- **并发限制**: 建议不超过 10 个并发请求
- **频率限制**: 建议每秒不超过 5 个请求
- **数据量限制**: 单次请求返回记录数不超过 50,000 条

### 优化建议
1. **使用摘要接口**: 当只需要统计信息时，使用 `/summary` 接口
2. **批量操作**: 多股票数据获取使用 `/batch` 接口
3. **缓存结果**: 对于相同请求，考虑客户端缓存
4. **分页处理**: 大数据量时使用分页或时间范围分割

## 版本更新

### API v1.0
- 基础分笔数据获取功能
- 单一数据源支持

### API v1.1 (当前版本)
- 统一架构，支持多数据源
- 增强的数据质量报告
- 批量处理接口
- 自动故障转移机制

## 支持

如有问题或建议，请联系开发团队或查看项目文档。