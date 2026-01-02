# 任务调度系统架构设计

> 本目录包含任务调度系统的完整架构设计文档。

## 文档目录

| 文档 | 说明 |
|:-----|:-----|
| [00_overview.md](./00_overview.md) | 总体概述与核心决策 |
| [01_current_issues.md](./01_current_issues.md) | 当前问题分析 |
| [02_target_architecture.md](./02_target_architecture.md) | 目标架构设计 (初版) |
| [03_smart_collection.md](./03_smart_collection.md) | 智能采集框架 |
| [04_implementation_roadmap.md](./04_implementation_roadmap.md) | 实施路线图 |
| **[05_final_architecture.md](./05_final_architecture.md)** | **最终确认方案** ⭐ |

## 核心结论 (已确认)

1. **完整微服务拆分**：gsd-api、gsd-sync、gsd-quality、task-orchestrator 独立仓库
2. **临时任务模式**：sync 和 quality 用完即销毁
3. **并行分片**：sync 支持 4 容器并行，10分钟→2.5分钟
4. **共享包**：gsd-shared 存放公共数据模型

---

**创建时间**: 2026-01-02  
**确认时间**: 2026-01-02
