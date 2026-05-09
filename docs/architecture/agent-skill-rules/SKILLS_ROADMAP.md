# 自动化辅助技能路线图 (Skills Roadmap)

> 为了进一步降低人工审计负担，规划以下三项核心技能。这些技能将作为 Agent 的“自动化工具箱”，在实施过程中被强制调用。

---

## 1. `skill:data-validator` (数据契约校验)

### 核心功能
- **静态审计**: 扫描 SQL 字符串，检查 `is_deleted = 0` 关键字及字段命名规范。
- **单位对比**: 联动 `TABLES_INDEX.md`，对代码中的数值赋值（如 `amount = ...`）进行量纲检查。
- **输出**: 产出审计报告。若发现冲突（如使用了 Tushare 的千元单位），强制中断实施并报警。

---

## 2. `skill:report-curator` (报告存证管家)

### 核心功能
- **真源提取**: 自动执行 `docker logs` 或 `mysql -e "SELECT..."`。
- **模板生成**: 将提取的证据片段自动填充进 `walkthrough.md` 的“验证结果”章节。
- **截图模拟**: 捕捉控制台表格输出，转化为 Markdown 格式的代码块。

---

## 3. `skill:schema-enforcer` (Schema 执法官)

### 核心功能
- **DDL 验证**: 拦截所有 `CREATE TABLE` 语句。
- **强约束检查**:
    - 是否包含 `created_at`, `updated_at`, `is_deleted`？
    - 是否包含 `idx_updated_at`？
    - 字符集是否为 `utf8mb4`？
- **自动补全**: 若 DDL 缺失“尾部三件套”，技能应能自动修正并提供补全建议。

---

## 实施阶段建议
1. **P1 (短期)**: 优先实现 `skill:report-curator` 的基础功能，强制规范 `walkthrough.md` 的质量。
2. **P2 (中期)**: 实现 `skill:data-validator`，解决最隐蔽的“单位陷阱”问题。
3. **P3 (长期)**: 将这些技能集成进 `parse-epic-story` 的 Task 切换逻辑中。
