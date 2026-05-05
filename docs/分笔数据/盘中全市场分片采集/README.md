# 盘中分笔数据采集系统技术文档中心

## 项目概览
本系统旨在实现 A 股全市场（~5,800 只股票）的实时分笔数据（Tick Data）采集。采用分布式架构，通过三节点分片（Sharding）均衡负载，确保低延迟入库与高稳定性。

### 核心指标
*   **采集范围**: 深沪 A 股全市场
*   **数据频率**: 实时 (约 3-5 秒/轮)
*   **存储引擎**: ClickHouse (本地采集，汇总存储)
*   **分布式架构**: Redis 动态分片 + 三节点并行

---

## 文档索引

### 1. [架构设计 (01_ARCH_DESIGN.md)](01_ARCH_DESIGN.md)
*   分布式分片逻辑 (`xxHash64`)
*   Redis 动态加载机制
*   数据流向示意图

### 2. [部署指南 (02_DEPLOYMENT_GUIDE.md)](02_DEPLOYMENT_GUIDE.md)
*   Node 41/58/111 角色定义
*   Docker Compose 分片配置
*   多阶段构建 (Docker build) 优化

### 3. [代码质量 (03_CODE_QUALITY.md)](03_CODE_QUALITY.md)
*   Redis 连接池与超时优化
*   熔断器 (Circuit Breaker) 集成
*   异步安全与并发锁控制

### 4. [运维监控 (04_OPERATIONS.md)](04_OPERATIONS.md)
*   主机名标记 (`hostname`) 实操
*   各节点健康状态检查命令
*   常见故障 (Redis 连接、权限) 排查

### 5. [用户手册 (05_USER_GUIDE.md)](05_USER_GUIDE.md)
*   ClickHouse 表结构详述
*   经典查询示例 (量价比分析)
*   各分段分片数据量参考

### 6. [数据网关 (06_MOOTDX_API_INTEGRATION.md)](06_MOOTDX_API_INTEGRATION.md)
*   Mootdx-API 接口规格
*   TDX 连接池与常用配置
*   性能调优与故障说明

### 7. [故障排除 (07_TROUBLESHOOTING.md)](07_TROUBLESHOOTING.md)
*   分布式数据流拓扑图
*   各阶段连接故障诊断 (Redis/API/TDX/CK)
*   运维快速命令指南

### 8. [数据校验 (08_INTRADAY_VALIDATION.md)](08_INTRADAY_VALIDATION.md)
*   午休与盘后校验逻辑
*   分布式环境下的幂等性补采
*   审计日志与手动运维指令

---
**最近更新**: 2026-01-21  
**状态**: ✅ 已在生产环境完成三节点上线验证
