# 远程数据采集服务 API 规范

## 需求方
- **服务**: get-stockdata (本地)
- **用途**: 数据质量修复时触发个股历史数据重新采集

---

## 需要的 API

### 1. 个股历史数据采集

**功能**: 采集指定股票的全部历史 K 线数据，写入 MySQL

```
POST /api/v1/collect/stock_history
```

**请求参数**:
```json
{
  "stock_code": "sh.600519",      // 必填，股票代码
  "start_date": "1990-01-01",     // 可选，开始日期，默认从上市日
  "end_date": "2025-12-31",       // 可选，结束日期，默认今天
  "clear_existing": true          // 可选，是否先清除 MySQL 中该股已有数据
}
```

**响应 (异步任务)**:
```json
{
  "status": "accepted",
  "task_id": "abc123",
  "message": "采集任务已启动",
  "estimated_time": 30
}
```

**响应 (同步完成，如果支持)**:
```json
{
  "status": "success",
  "stock_code": "sh.600519",
  "records_collected": 5732,
  "date_range": ["2001-08-27", "2025-12-31"]
}
```

---

### 2. 采集任务状态查询

**功能**: 查询采集任务执行状态

```
GET /api/v1/collect/task/{task_id}
```

**响应**:
```json
{
  "task_id": "abc123",
  "status": "running",   // pending | running | success | failed
  "progress": 60,        // 进度百分比
  "stock_code": "sh.600519",
  "records_collected": 3500,
  "error": null
}
```

---

### 3. 批量采集（可选）

**功能**: 批量采集多只股票

```
POST /api/v1/collect/batch
```

**请求参数**:
```json
{
  "stock_codes": ["sh.600519", "sz.000001"],
  "start_date": "2024-01-01"
}
```

---

## 数据写入要求

采集服务需将数据写入 MySQL，表结构如下：

```sql
-- 表名: stock_kline_daily
CREATE TABLE stock_kline_daily (
  code VARCHAR(20) NOT NULL,        -- 股票代码 (sh.600519)
  trade_date DATE NOT NULL,         -- 交易日期
  open DECIMAL(10,2),               -- 开盘价
  high DECIMAL(10,2),               -- 最高价
  low DECIMAL(10,2),                -- 最低价
  close DECIMAL(10,2),              -- 收盘价
  volume BIGINT,                    -- 成交量
  amount DECIMAL(20,2),             -- 成交额
  turnover DECIMAL(10,4),           -- 换手率
  pct_chg DECIMAL(10,4),            -- 涨跌幅
  created_at DATETIME DEFAULT NOW(),
  PRIMARY KEY (code, trade_date)
);
```

---

## 调用场景

1. **个股数据修复**: get-stockdata 检测到某股票数据有问题，触发重新采集
2. **新股补采**: 发现新上市股票，触发历史数据采集
3. **批量回填**: 初始化系统时批量采集

---

## 回调通知（可选）

如果支持回调，采集完成后通知 get-stockdata：

```
POST http://{get-stockdata}/api/v1/callback/collect_complete
```

```json
{
  "task_id": "abc123",
  "stock_code": "sh.600519",
  "status": "success",
  "records_collected": 5732
}
```

get-stockdata 收到回调后会自动触发同步。

---

## 优先级

| API | 优先级 | 说明 |
|:----|:------|:----|
| `POST /collect/stock_history` | **P0** | 核心功能，必须实现 |
| `GET /collect/task/{id}` | **P1** | 异步任务需要 |
| `POST /collect/batch` | P2 | 可后续实现 |
| 回调通知 | P2 | 可用轮询替代 |
