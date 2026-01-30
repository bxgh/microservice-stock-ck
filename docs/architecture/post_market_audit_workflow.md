# 盘后数据审计与自愈流程 (Post-Market Audit Workflow V2)

## 1. 概述
本工作流定义了每日盘后 (17:30+) 执行的分笔数据质量审计与自动修复流程。
流程采用 **Check & Wait** 机制，严格依赖 K 线数据就绪，通过 **SQL 批量聚合 + 内存高速对账** 的方式，对沪深全市场股票进行 L1/L2 校验，并对异常数据执行物理清洗与补采。

## 2. 核心原则
*   **依赖栅栏**: 无 K 线，不校验。
*   **范围对齐**: 严格**剔除北证 (BJ/8xx/4xx)** 股票，仅处理沪深主板/创业/科创。
*   **物理清洗**: 所有的 L2 校验失败 (Invalid) 均视为脏数据，必须先 `DELETE` 再补采。

## 3. 流程图

```mermaid
graph TD
    Start[Job 启动] --> Filter[1. 确定目标范围<br/>(Exclude BJ)]
    Filter --> WaitK[2. K线就绪检查<br/>(Check & Wait)]
    
    WaitK -- "覆盖率 < 99%" --> Sleep[等待 5min]
    Sleep --> |Retry < 12| WaitK
    WaitK -- "覆盖率 >= 99%" --> Fetch[3. 全量数据拉取]
    
    subgraph "内存高速比对"
        Fetch --> |Batch SQL| TickAgg[Tick 聚合指标]
        Fetch --> |Batch SQL| KlineRef[K线 参考指标]
        TickAgg & KlineRef --> VectorCalc[4. L1/L2 向量化对账]
    end
    
    VectorCalc --> Result{结果分类}
    Result --> |Missing| ListM[缺失名单]
    Result --> |Invalid| ListI[脏数据名单]
    Result --> |Valid| Pass[通过]
    
    ListI --> Purge[5. 物理删除 (DELETE)]
    Purge --> Repair[6. 执行补采 (Sync)]
    ListM --> Repair
    
    Repair --> Verify[7. 最终报告]
    Verify --> End((结束))
```

## 4. 详细步骤

### 4.1 范围界定 (Scope Definition)
*   **分母来源**: Redis `stock_list`。
*   **过滤规则**: 剔除代码前缀为 `bj` 或以 `8`、`4` 开头的股票。
*   **目的**: 确保 Tick (不含北证) 与 K 线 (含北证) 的比较范围一致，防止北证股票被误判为 Missing。

### 4.2 依赖检查 (Dependency Check)
*   **目标**: 确保作为“裁判员”的日 K 线数据已就绪。
*   **逻辑**: 
    *   查询 `stock_data.stock_kline_daily` 当日记录数。
    *   若 `K线数 / 目标股票数 < 99%`，则进入等待循环。
    *   最大等待 60 分钟，超时报警退出。

### 4.3 高速比对 (Vectorized Validation)
采用 **SQL 批量聚合 + Python 内存比对** 模式，避免数千次 DB 交互。

*   **Query A (Tick)**: 
    ```sql
    SELECT stock_code, count(), sum(volume), argMax(price, tick_time)
    FROM tick_data_intraday WHERE date=Today GROUP BY stock_code
    ```
*   **Query B (KLine)**:
    ```sql
    SELECT stock_code, volume, close_price 
    FROM stock_kline_daily WHERE date=Today
    ```
*   **内存逻辑**:
    1.  **L1 存在性**: Tick 表中无此 Code -> **Missing**。
    2.  **L2 准确性**: 
        *   `abs(TickPrice - KPrice) > 0.01` -> **Invalid**。
        *   `abs(TickVol - KVol)/KVol > 0.02` -> **Invalid**。

### 4.4 物理清洗 (Physical Purge)
对于被判定为 **Invalid** 的股票，说明库中存在脏数据（如乱序、重复、截断），必须物理清除以防堆积。

*   **操作**: 
    ```sql
    ALTER TABLE tick_data_intraday ON CLUSTER default
    DELETE WHERE trade_date = '{date}' AND stock_code IN ('code1', 'code2'...)
    ```

### 4.5 靶向补采 (Repair)
*   **对象**: `Missing List` + `Invalid List` (已清洗)。
*   **工具**: `TickSyncService.sync_stocks`。
*   **并发**: 建议 32-64 并发。

## 5. 异常处理
*   **K线源故障**: 若等待 1 小时后 K 线仍未就绪，作业 Fail，不执行任何清洗或补采（宁缺毋滥）。
*   **补采失败**: 补采后若仍未通过校验，仅记录报警，不再死循环重试。

