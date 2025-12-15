# Tencent Cloud Akshare API 接口文档

## 概述
部署在腾讯云服务器 (124.221.80.250:8111) 上的 Python 服务，旨在为内网环境提供稳定的 Akshare 数据访问通道。该服务直接在云端调用 Akshare 接口，并将结果序列化为 JSON 返回，解决了本地内网访问部分数据源受限的问题。

- **服务版本**: 2.4.0
- **基础 URL**: `http://124.221.80.250:8111`
- **代理访问**: 需通过内网 HTTP 代理 (`192.168.151.18:3128`) 访问

## 接口列表

### 1. 基础接口

#### 健康检查
- **URL**: `/health`
- **Method**: `GET`
- **描述**: 检查服务存活状态及 Akshare 版本。
- **Response**:
  ```json
  {
    "status": "healthy",
    "timestamp": "2025-12-15T18:00:00.000",
    "akshare_version": "1.17.94"
  }
  ```

### 2. 榜单数据 (Rankings) - Smart Money

#### 人气榜
- **URL**: `/api/v1/rank/hot`
- **Method**: `GET`
- **描述**: 东方财富个股人气榜。

#### 飙升榜
- **URL**: `/api/v1/rank/surge`
- **Method**: `GET`
- **描述**: 东方财富个股飙升榜。

#### 涨停池
- **URL**: `/api/v1/rank/limit_up`
- **Method**: `GET`
- **Params**:
  - `date`: 日期 (YYYYMMDD)
- **描述**: 指定日期的涨停股池。

### 3. 市场行情 (Market Data)

#### 实时行情
- **URL**: `/api/v1/stock/spot`
- **Method**: `GET`
- **描述**: 全市场实时行情快照 (含动态PE/PB/市值)。

#### 历史K线
- **URL**: `/api/v1/stock/hist/{symbol}`
- **Method**: `GET`
- **Path Params**:
  - `symbol`: 股票代码 (如 600519)
- **Params**:
  - `start_date`: 开始日期 (YYYYMMDD)
  - `end_date`: 结束日期 (YYYYMMDD)
  - `adjust`: 复权方式 (qfq/hfq/None, 默认 qfq)

### 4. 财务数据 (Financials) - EPIC-002

#### 财务报表摘要
- **URL**: `/api/v1/finance/statements/{symbol}`
- **Method**: `GET`
- **描述**: 历史季度核心指标摘要 (EPS, ROE 等)。

#### 详细财务报表
- **URL**: `/api/v1/finance/sheet/{symbol}`
- **Method**: `GET`
- **Params**:
  - `type`: 报表类型 (`main`=主要指标, `income`=利润表, `balance`=资产负债表, `cash`=现金流量表)

#### 历史估值指标
- **URL**: `/api/v1/valuation/history/{symbol}`
- **Method**: `GET`
- **描述**: 历史每日估值指标 (PE, PB, PS 等)。
- **注意**: 使用新浪/东财财务指标接口替代了原有的亿牛网接口。

### 5. 行业数据 (Industry)

#### 行业列表
- **URL**: `/api/v1/industry/list`
- **Method**: `GET`
- **描述**: 东财行业板块列表。

#### 行业成分股
- **URL**: `/api/v1/industry/cons/{board_code}`
- **Method**: `GET`
- **Path Params**:
  - `board_code`: 板块代码 (如 BK0474)

## 维护指南

### 更新服务
1. 将新的 `akshare_api.py` 上传至 `/opt/akshare-api/`
2. 重启服务: `sudo systemctl restart akshare-api`
3. 查看日志: `sudo journalctl -u akshare-api -f`
