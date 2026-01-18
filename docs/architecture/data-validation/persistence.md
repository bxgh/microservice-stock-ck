# 数据持久化标准 (Data Persistence Standards)

本文档定义了数据校验结果在腾讯云 MySQL 中的存储结构与访问契约，由 `libs/gsd-shared` 中的 `AuditRepository` 统一实现。

## 1. 存储架构

校验结果采用“汇总-详情”的两层存储模式，主要库名为 `alwaysup`。

### 1.1 汇总表 (data_audit_summaries)
存储单次校验任务的总体结论与元数据。

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| **id** | BIGINT | 自增主键 |
| **data_type** | VARCHAR(32) | 数据类型 (`tick`, `kline`, `market`, `stock_list`) |
| **target** | VARCHAR(64) | 校验对象 (股票代码、日期或 `all`) |
| **trade_date** | DATE | 交易日期 (逻辑主键成员) |
| **level** | VARCHAR(16) | 最终状态 (`PASS`, `WARN`, `FAIL`) |
| **issue_count** | INT | 发现的问题总数 |
| **description** | TEXT | 关键指标简述 (如 "覆盖率 99%") |
| **idemp_key** | VARCHAR(128) | 幂等键 (`data_type:target:trade_date`) |

### 1.2 详情表 (data_audit_details)
存储具体的规则触发详情与上下文。

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| **summary_id** | BIGINT | 关联汇总表 ID |
| **dimension** | VARCHAR(64) | 校验维度 (`continuity`, `coverage`, `consistency`) |
| **level** | VARCHAR(16) | 该维度的状态 |
| **message** | TEXT | 错误/告警描述信息 |
| **context** | JSON | 详细指标数据 (如具体缺口时段) |

## 2.  Repository 开发指南

### 2.1 代码路径
`libs/gsd-shared/gsd_shared/repository.py` -> `AuditRepository`

### 2.2 核心方法
```python
async def save_result(self, result: ValidationResult) -> bool:
    """
    保存校验结果。
    逻辑：
    1. 开启事务。
    2. UPSERT 到 data_audit_summaries (基于 idemp_key)。
    3. 获取 summary_id，DELETE 旧的详情记录。
    4. INSERT 新的 data_audit_details。
    5. 提交事务。
    """
```

### 2.3 异常处理
- 事务级别：READ COMMITTED。
- 采用 `ON DUPLICATE KEY UPDATE` 确保并发幂等。
- 自动处理 Pydantic 模型与 MySQL 数据类型的转换。

## 3. SQL 查询示例

### 3.1 查询今日全市场健康度
```sql
SELECT * FROM alwaysup.data_audit_summaries 
WHERE data_type = 'market' AND trade_date = CURDATE();
```

### 3.2 查看具体个股的异常详情
```sql
SELECT d.* FROM alwaysup.data_audit_details d
JOIN alwaysup.data_audit_summaries s ON d.summary_id = s.id
WHERE s.target = '600519' AND s.trade_date = '2026-01-18';
```

## 4. 维护与清理
- **历史清理**: 每周日执行维护任务，清理 180 天前的审计详情。
- **性能优化**: 对 `idemp_key` 和 `trade_date` 建立索引。

