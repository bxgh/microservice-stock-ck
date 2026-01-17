# 定向个股数据补充 (stock_data_supplement)

## 1. 任务概述

`stock_data_supplement` 是一个多维度的综合补采任务，支持同时补充指定股票的多种类型数据（Tick、K线、财务数据等）。该任务通常用于“个股体检”或“紧急修复”场景。

*   **Task ID**: `stock_data_supplement`
*   **服务**: `gsd-worker`
*   **执行入口**: `jobs.supplement_stock`

## 2. 核心参数

通过 `task_commands.params` JSON 字段传递参数：

| 参数名 | 必填 | 类型 | 说明 | 示例 |
|:---|:---|:---|:---|:---|
| `stocks` | 是 | Array | 股票代码列表 | `["000001", "600519"]` |
| `data_types` | 否 | Array | 需要补充的数据类型，默认 `["tick"]` | `["tick", "kline", "financial"]` |
| `date` | 否 | String | 指定单日 (YYYYMMDD) | `"20260115"` |
| `date_range` | 否 | String | 指定日期范围 (YYYYMMDD-YYYYMMDD) | `"20260101-20260115"` |
| `priority` | 否 | String | 优先级，默认 `normal` | `"high"` |

## 3. 支持的数据类型

| 类型值 | 描述 | 数据源 |
|:---|:---|:---|
| `tick` | 分笔成交细单 | TDX 历史行情接口 |
| `kline` | 日K线数据 | TDX K线接口 |
| `financial` | 基础财务数据 | TDX 财务数据接口 |

## 4. 执行流程

1.  **参数解析**: 解析传入的股票列表和数据类型。
2.  **引擎初始化**: 启动 `DataSupplementEngine`。
3.  **多维采集**: 
    *   遍历每只股票。
    *   按顺序执行各类型的采集器（TickCollector, KLineCollector 等）。
    *   将结果写入 ClickHouse。
4.  **结果汇总**: 输出成功/失败统计。

## 5. 触发示例

### SQL 触发

```sql
-- 场景: 紧急修复 000001 和 600519 在 1月15日 的所有数据（Tick + K线）
INSERT INTO task_commands (task_id, params) 
VALUES ('stock_data_supplement', '{
    "stocks": ["000001", "600519"], 
    "data_types": ["tick", "kline"], 
    "date": "20260115"
}');
```
