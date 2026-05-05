# 股票代码查询与管理 API

本文档描述了 A 股股票代码数据采集系统中的股票代码查询、管理及导出 API 接口。

## 📋 基础信息

- **服务器地址**: `http://124.221.80.250:8000`
- **基础路径**: `/api/v1`
- **数据格式**: JSON
- **交易所代码**: `SH` (上证), `SZ` (深证), `BJ` (北证)

## 🔍 查询接口

### 1. 获取股票代码列表 (分页)

**接口地址**: `GET /stocks`

**查询参数**:
- `exchange` (string, 可选): 交易所代码 (SH/SZ/BJ)
- `security_type` (string, 可选): 证券类型 (Stock, Index, ETF 等)
- `is_active` (boolean, 可选): 是否活跃
- `name_search` (string, 可选): 按名称模糊搜索
- `skip` (int, 可选, 默认 0): 跳过记录数
- `limit` (int, 可选, 默认 100): 返回记录数限制 (最大 1000)

**响应示例**:
```json
{
  "items": [
    {
      "id": 1,
      "standard_code": "000001",
      "name": "平安银行",
      "exchange": "SZ",
      "security_type": "Stock",
      "is_active": true,
      "formats": {"tushare": "000001.SZ"},
      "list_date": "1991-04-03",
      "delist_date": null,
      "data_source": "akshare",
      "last_updated": "2024-01-09T10:00:00"
    }
  ],
  "total": 5300,
  "skip": 0,
  "limit": 100,
  "has_more": true
}
```

### 2. 获取全量股票代码简要信息 (一键导出用)

**接口地址**: `GET /stocks/all`

**功能描述**: 获取全市场代码、名称、类型和交易所的简要列表，不分页。

**查询参数**:
- `exchange`, `security_type`, `is_active` (同上)

**响应示例**:
```json
{
  "items": [
    {
      "standard_code": "000001",
      "name": "平安银行",
      "security_type": "Stock",
      "exchange": "SZ"
    }
  ],
  "total": 5300
}
```

### 3. 获取单只股票详情

**接口地址**: `GET /stocks/{standard_code}`

**路径参数**:
- `standard_code`: 6 位股票代码

**查询参数 (可选)**:
- `security_type`, `exchange`: 当代码在不同市场/类型重复时用于唯一确定

---

## 🛠️ 管理接口

### 4. 创建股票代码记录

**接口地址**: `POST /stocks`

**请求体**:
```json
{
  "standard_code": "688001",
  "name": "华兴源创",
  "exchange": "SH",
  "security_type": "Stock",
  "list_date": "2019-07-22",
  "data_source": "manual"
}
```

### 5. 更新股票代码记录

**接口地址**: `PUT /stocks/{standard_code}`

**查询参数 (必须)**:
- `security_type`, `exchange`: 用于精确定位记录

---

## 💾 导出接口

### 6. 数据导出

**接口地址**: `GET /stocks/export`

**查询参数**:
- `format`: `json` 或 `csv`
- `exchange`, `security_type`, `is_active`, `name_search` (过滤条件)

**响应**: 返回对应的文件流。
