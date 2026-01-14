# 数据门禁 (Gate-3): 盘后深度审计与对账

## 1. 目标
在收盘且所有采集完成后 (19:18)，进行最严格的“数据大考”：
1. **全量覆盖率校验** - 确认当日行情数据是否 100% 颗粒归仓
2. **时段完整性检查** - 深度检查所有股票是否覆盖 09:25-15:00 无断点
3. **价格一致性对账** - 比对分笔落表数据与日 K 线收盘价，确保无逻辑偏差

## 2. 执行逻辑
- **调度时间**: 每个交易日 `19:18`
- **校验对象**: 当日 (T) 全量历史数据
- **核心指标**:
    - 全市场 K线覆盖率 > 99%
    - 全市场分笔时段覆盖率 = 100%
    - 收盘价对账差异率 < 0.01%

## 3. 修复机制
- **即时修复**: 发现空洞立即触发 `repair_tick` 任务。
- **报告生成**: 生成当日《数据质量审计白皮书》，作为后续回测的质量凭证。

## 4. 告警通知
- **深度报告**: 包含抽样对账详情及异常点分析报告。

## 5. 检查结果入库 (Persistence)

### 5.1 云端数据表 (`alwaysup.data_gate_audits`)
极简审计表，仅保留核心状态：

```sql
CREATE TABLE IF NOT EXISTS `data_gate_audits` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `trade_date` DATE NOT NULL COMMENT '交易日期',
    `gate_id` VARCHAR(20) NOT NULL COMMENT 'GATE_1/2/3',
    `is_complete` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1: 完整, 0: 不完整',
    `description` VARCHAR(255) COMMENT '简要结果说明 (如: K线99% 分笔100%)',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE INDEX `idx_date_gate` (`trade_date`, `gate_id`)
) COMMENT='精简版数据门禁审计历史';
```

### 5.2 入库流程 (Simplified Flow)
1. **本地执行**: `PostMarketGateService` 完成校验。
2. **状态判定**: 若 `status == 'SUCCESS'` 则 `is_complete = 1`，否则为 `0`。
3. **极简写入**: 仅写入日期、门禁ID、是否完整以及一行文本摘要。

### 5.3 前端交互与任务启动
1. **状态展示**: 小程序根据 `status` 字段渲染卡片（绿色/橙色/红色）。
2. **详情下钻**: 点击卡片展示 `metrics` 中的异常股票详情。
3. **二次补采**: 
   - 对于 `WARNING/ERROR` 的记录，前端提供“一键补采”按钮。
   - 点击按钮调用 `cloud-api` 向 `task_commands` 表插入 `repair_tick` 指令。
   - 内网 `CommandPoller` 捕获指令并执行，形成质量闭环。