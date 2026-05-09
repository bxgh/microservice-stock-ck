# 根目录清理与整洁规范方案

> [!IMPORTANT]
> **状态**：已实施 (2026-05-09)
> **执行人**：Antigravity

## 1. 背景与现状
当前项目根目录存在大量一次性测试脚本 (`.py`)、调试日志 (`.log`) 和临时 Shell 脚本 (`.sh`)。这些文件干扰了对项目核心结构的理解，增加了维护成本，且违反了 `AGENTS.md` 中关于“不污染生产代码目录”的规定。

## 2. 整理原则
- **物理隔离**：所有非项目核心配置、非全局说明文档的文件，严禁存放在根目录。
- **分类归档**：根据文件属性（日志、临时脚本、持久工具）移动到对应的二级目录。
- **自动化清理**：建立定期清理或自动归档机制。

## 3. 详细分类迁移方案

### 3.1 日志文件 (`*.log`)
- **目标目录**：`logs/archive/` 或 `logs/manual/`
- **处理方式**：
  - 将根目录下所有 `sync_*.log`, `repair_*.log`, `gost_*.log` 等文件移动至 `logs/manual/`。
  - 对于超过 30 天的日志，直接物理删除。
  - **后续规范**：运行脚本时，必须使用重定向将输出保存到 `logs/` 目录下，禁止直接在当前目录生成。

### 3.2 临时测试/修复脚本 (`*.py`)
- **目标目录**：`scratch/history/`
- **处理方式**：
  - 属于特定微服务的测试脚本，移动到该微服务目录下的 `scratch/` 目录。
  - 跨模块的一次性脚本（如 `check_tasks.py`, `verify_fixes.py`）移动到根目录的 `scratch/history/`。
  - **后续规范**：所有开发过程中的临时代码必须在 `scratch/` 目录下创建，git 提交前必须清理。

### 3.3 运维与部署脚本 (`*.sh`, `*.service`)
- **目标目录**：`scripts/ops/` 或 `deploy/services/`
- **处理方式**：
  - 常用运维脚本（如 `clean_redis.py`, `fix_iptables.sh`）移动到 `scripts/maintenance/`。
  - Systemd 服务定义文件（如 `gost-mysql-tunnel.service`）移动到 `deploy/services/`。

## 4. 根目录白名单 (Whitelist)
根目录仅允许保留以下文件/目录：
- **目录**：`apps/`, `services/`, `libs/`, `packages/`, `docs/`, `deploy/`, `scripts/`, `logs/`, `scratch/`, `tests/`, `infrastructure/`, `proto/`, `migrations/`, `data/`, `venv/`, `UI/`
- **文件**：`.gitignore`, `AGENTS.md`, `CLAUDE.md`, `PROJECT_OVERVIEW.md`, `TABLES_INDEX.md`, `docker-compose*.yml`, `pyproject.toml`, `requirements.txt` 等核心工程文件。

## 5. 实施步骤
1. **创建目录**：确保 `logs/manual/` 和 `scratch/history/` 存在。
2. **批量移动**：
   ```bash
   # 移动日志
   mv *.log logs/manual/
   # 移动临时 Python 脚本
   mv check_*.py verify_*.py repair_*.py scratch/history/
   # 移动运维脚本
   mv fix_*.sh scripts/maintenance/
   ```
3. **清理残留**：删除已知无用的 `.bak`, `.tmp` 文件。

## 6. 维护机制
- **Agent 门禁**：在 `AGENTS.md` 中增加根目录审计规则，禁止 Agent 在根目录新建文件。
- **提交检查**：开发者在 Push 代码前需检查根目录状态。
