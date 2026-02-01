# 测试执行 CheckList：历史分笔补采专题 (Node 41)

## 0. 基本信息
- **测试日期**: 2026-01-20
- **执行环境**: Node 41 (Server 41)
- **核心逻辑**: V4.0 集中化补采 + AI 韧性自愈
- **测试目标**: 验证单节点 60 并发稳定性、集群同步清理 (ON CLUSTER) 有效性、北证强制过滤、及 AI 容错降级逻辑。

---

## 1. 测试准备 (Preparation)
- [ ] 检查 Node 41 连接池配置：`TDX_POOL_SIZE` 建议 80。
- [ ] 检查环境变量：确保 `SILICONFLOW_API_KEY` 已注入（用于 AI 审计）。
- [ ] 样本观察：记录当前 `stock_data.tick_data` 中 `trade_date = '2026-01-20'` 的总条数。

---

## 2. 第一阶段：全量重建与物理清场 (Full Sync)
**操作说明**: 执行该指令将清空集群内指定日期的所有旧数据，并按 K 线推导出的名单重新抓取。

- [ ] **下发指令**:
  ```sql
  INSERT INTO alwaysup.task_commands (task_id, params, status) 
  VALUES (
    'repair_tick', 
    '{"date": "20260120", "mode": "full", "scope": "all", "concurrency": 60}', 
    'pending'
  );
  ```
- [ ] **执行验证**: 
    - 检查日志中是否出现 `ALTER TABLE ... ON CLUSTER stock_cluster DELETE ...`。
    - 确认 `fetch_sync_list` 提取的代码已标准化（6位），且不含 `4/8/9` 前缀。
- [ ] **状态检查**: 登录数据库确认 `trade_date = '2026-01-20'` 数据量是否随采集进度稳步增长。

---

## 3. 第二阶段：专项质量审计 (Quality Audit)
**操作说明**: 采集完成后，手动触发针对该日期的精准对账审计。

- [ ] **下发指令**:
  ```sql
  INSERT INTO alwaysup.task_commands (task_id, params, status) 
  VALUES (
    'adhoc_audit', 
    '{"date": "2026-01-20", "threshold": 200}', 
    'pending'
  );
  ```
- [ ] **结果分析**:
    - [ ] `Invalid` 数量应极低（通常 < 50）。
    - [ ] 确认审计结果中 `failed_codes` 与 `abnormal_list` 不包含北交所股票。
    - [ ] 记录审计判定的 `action`（应为 `AI_AUDIT`）。

---

## 4. 第三阶段：AI 韧性自愈与容错 (Directed Repair)
**操作说明**: 模拟 AI 介入过滤停牌股，并执行最后的定向精准捕。

- [ ] **下发指令 (基于审计输出的 abnormal_list)**:
  ```sql
  -- 将下方 JSON 中的 stock_list 替换为审计发现的实际异常代码
  INSERT INTO alwaysup.task_commands (task_id, params, status) 
  VALUES (
    'stock_data_supplement', 
    '{"date": "20260120", "sys_action": "AI_AUDIT", "sys_missing": "[\"000001\", \"600519\"]", "force_concurrency": 20}', 
    'pending'
  );
  ```
- [ ] **容错测试 (可选)**:
    - 临时禁用网络，验证 `ai_quality_gatekeeper.py` 是否能优雅降级，直接输出全部输入名单进行补采，而不报错崩溃。
- [ ] **最终确认**: 重复执行一次 `adhoc_audit` 指令，状态应显示 `ALL VALID` 或异常数极低且已由 AI 确认无误。

---

## 5. 验收标准
- [ ] 全程未触碰当日 (Intraday) 采集表的逻辑。
- [ ] 分笔数据覆盖率（剔除北证后） > 99.5%。
- [ ] 物理清理指令生效，无重复 Tick 数据（通过 `verify_overlap.py` 抽样）。
- [ ] AI 降级逻辑生效，无盲目全量重洗。
