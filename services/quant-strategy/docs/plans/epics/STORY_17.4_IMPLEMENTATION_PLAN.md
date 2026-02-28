# Story Implementation Plan

**Story ID**: 17.4  
**Story Name**: 端到端数据采集定时任务与真实数据库集成验证  
**开始日期**: 2026-02-28  
**预期完成**: 2026-02-28  
**负责人**: AI Assistant  
**AI模型**: DeepSeek-V3 (模拟)

---

## 📋 Story概述

### 目标
通过前三个 Story，收集器和持久层都已经具备。在这个 Story 中，我们会将 `altdata-source` 结合现有的 FastAPI 引擎及定时任务框架（或 API 触发），实现全链路“采集 -> 加工 -> 保存”测试，证实其完全运转并可以在生产环境中自动执行。

### 验收标准
- [ ] 开发调度模块 `jobs/sync.py` 负责组装流程。
- [ ] 开发手动调试后门接口 `/api/v1/altdata/trigger_sync`，支持手动发信号触发所有配置 `repositories.yaml` 库的搜集。
- [ ] 在 `docker-compose.dev.yml` （如果存在）中进行容器化真实测试，或者在机器上直连 `ClickHouse` 写入。
- [ ] 确保控制台打印了拉取 5 个标签并各自写入成功的日志。

### 依赖关系
- **依赖Story**: Story 17.1 (基础)、17.2 (提取), 17.3 (插入)
- **环境条件**: 测试使用的 `GITHUB_TOKENS` 及本地 ClickHouse 处于 Up 状态。

---

## 🎯 需求分析

### 功能需求
1. **触发与控制**: 提供 API 并绑定后台执行逻辑可以快速拉起全量抓取。
2. **作业组装**: `Job` 实例化 `GitHubClient`, `GitHubCollector`, `ClickHouseDAO`。遍历 `ConfigLoader` 所有仓库，并汇总为一份巨大 `List[RepoMetrics]` 分批保存数据库以免大量数据长连接丢失。因为这只有 5 项配置，暂且用一把梭插入即可。

---

## 🏗️ 技术设计

### 核心组件

#### 组件1: `jobs/sync.py`
**职责**: 系统运行时的后台同步任务代码，包含从 Config -> Collector -> DB 的串联代码。

#### 组件2: `api/trigger.py`
**职责**: FastAPI 的 Router，绑定 `POST /altdata/trigger_sync` 路由。返回拉取被提交到后台运行的消息机制 (或者阻塞等待并返回值)。测试需要，我们采纳**可挂起执行** (`BackgroundTasks`) 方式，立刻返回 "Accept"。

---

## 📁 文件变更

### 新增文件
- [ ] `services/altdata-source/src/jobs/sync.py`
- [ ] `services/altdata-source/src/api/trigger.py`

### 修改文件
- [ ] `services/altdata-source/src/main.py` (注册新的 Router)

---

## 🔄 实现计划

### Phase 1: 编写全链路调度 (Job & API)
**预期时间**: 1 小时
- [ ] 完成 `sync_github_metrics` 函数调用链路。
- [ ] 开发并注入 `/trigger_sync` 路由。

### Phase 2: 测试环境准备与集成
**预期时间**: 2 小时
- [ ] 在 `.env` 中提供真实的 `GITHUB_TOKENS` （根据之前会话提供的假定 token，但使用本地直联模式跳过真实网域或针对特定的一个开源库尝试真实调用）。
- [ ] 启动服务并发起 `curl POST` 验证数据库表中出现真实数据特征。
- [ ] 导出 `STORY_17.4_QUALITY_REPORT.md` (或合并在 Walkthrough 中)。

---

## 🚨 风险与缓解

| 风险 | 影响 | 可能性 | 缓解措施 |
|------|------|--------|----------|
| 本地无真实 ClickHouse 连线 | 致命 | 低 | 修改本机或使用 Docker `docker run -d -p 8123:8123 yandex/clickhouse-server` 快速搭建起临时的供其写入的存储层，保证集成真实。 |
| GitHub 严格屏蔽 | 中等 | 中 | 测试库仅限定使用少数组织尝试，并在日志中观察限流回执。 |

---

*模板版本: 1.0*  
