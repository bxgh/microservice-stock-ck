# 数据门禁 (Gate-2): 盘中实时采集监控

## 1. 目标
在交易时段内 (09:25-15:00)，持续监控采集稳定性：
1. **服务心跳校验** - 确保 `snapshot-recorder` 和 `tick-collector` 容器活跃
2. **流量水位监控** - 检测分笔数据流是否出现断崖式下跌（断流告警）
3. **延迟控制** - 监控从行情源到 ClickHouse 的写入延迟

## 2. 执行逻辑
- **调度时间**: 盘中定时轮询 (建议每 30 分钟) 或 Promethues 监控告警触发
- **校验对象**: 当前 (T) 实时流
- **核心指标**:
    - 活跃 Shards 数量 = 3
    - 分笔流心跳间隔 < 60s
    - Redis 队列堆积量 < 10,000

## 3. 容错机制
- **自动重启**: 检测到服务挂掉时由 Docker/K8s 重启。
- **动态重连**: 采集服务内部逻辑应具备行情源自动切线能力。

## 4. 告警通知
- **高优先级告警**: 发生断流或延迟超过阈值时，立即通过企业微信推送。

## 5. 检查结果入库 (Persistence)

### 5.1 云端数据表 (`alwaysup.data_gate_audits`)
共享极简审计表，仅记录核心就绪状态：

```sql
CREATE TABLE IF NOT EXISTS `data_gate_audits` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `gate_id` VARCHAR(20) NOT NULL COMMENT 'GATE_1/2/3',
    `is_complete` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1: 完整, 0: 不完整',
    `description` VARCHAR(255) COMMENT '简要结果说明 (如: 心跳:OK 延迟:<1s 断流:无)',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE INDEX `idx_date_gate` (`trade_date`, `gate_id`)
) COMMENT='精简版数据门禁审计历史';
```

### 5.2 入库流程 (Simplified Flow)
1. **本地执行**: 监控服务检测到异常或定时上报。
2. **状态判定**: 若心跳正常且无断流，则 `is_complete = 1`。
3. **文本摘要**: 在 `description` 中记录关键延迟或水位信息。
4. **极简写入**: 异步写入云端 MySQL。
