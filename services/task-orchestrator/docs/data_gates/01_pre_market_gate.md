# 数据门禁 (Gate-1): 盘前准入与名单校验

## 1. 目标
在每个交易日开盘前 (09:00)，确保系统具备新一交易日的运行条件：
1. **股票名单同步 (核心P0)** - 检查全市场股票名单（上市、退市、停牌）是否已同步为最新，防止遗漏新股或采集已退市个股。
2. **Redis 采集队列校验** - 验证 Redis 中的采集名单与数据库是否一致，确保常驻采集服务 (`snapshot-recorder` 等) 读取的是最新配置。
3. **系统环境就绪** - 快速检测 ClickHouse、Redis 连接状态及昨日数据补采结果 (Gate-3 最终态)。

## 2. 执行逻辑
- **调度时间**: 每个交易日 `09:15`
- **校验对象**: 
    - 股票名单 (Master List)
    - Redis 缓存名单
    - 昨日补采状态 (Gate-3)
- **核心指标**:
    - 名单一致性 = 100%
    - 基础服务 (DB/Cache) 心跳 = 正常
    - 昨日补采结果 = SUCCESS

## 3. 响应机制
- **名单更新**: 若发现名单落后（如今日有新股上市），立即触发 `sync_stock_list` 任务。
- **采集重启**: 若 Redis 名单更新，可能需要发送信号重启或热更新采集容器。
- **阻断告警**: 若核心名单同步失败，发送高优先级告警，提示可能影响今日实时数据采集。

## 4. 告警通知
- 发送“盘前准入报告”至企业微信。
- 重点标注：**[名单更新]** 状态及 **[服务心跳]** 状态。

## 5. 检查结果入库 (Persistence)

### 5.1 云端数据表 (`alwaysup.data_gate_audits`)
共享极简审计表：

```sql
CREATE TABLE IF NOT EXISTS `data_gate_audits` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `gate_id` VARCHAR(20) NOT NULL COMMENT 'GATE_1/2/3',
    `is_complete` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1: 完整, 0: 不完整',
    `description` VARCHAR(255) COMMENT '简要结果说明 (如: 名单已同步, 服务心跳正常)',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE INDEX `idx_date_gate` (`trade_date`, `gate_id`)
) COMMENT='精简版数据门禁审计历史';
```

### 5.2 入库流程 (Simplified Flow)
1. **本地执行**: `PreMarketGateService` 完成名单校验与环境检测。
2. **状态判定**: 若名单一致且核心服务连通，则 `is_complete = 1`。
3. **极简写入**: 通过隧道写入云端 MySQL。

## 6. 前端交互与一键更新
1. **状态展示**: 小程序展示“盘前就绪”状态。
2. **一键同步**: 
   - 若状态为“不完整”（名单未更新），前端提供“同步名单”按钮。
   - 点击按钮向 `task_commands` 插入 `sync_stock_list` 指令，实现准入修复。


