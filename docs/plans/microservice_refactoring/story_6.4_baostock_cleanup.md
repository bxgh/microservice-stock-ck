# Story 6.4: BaoStock Logic & Cleanup

## 目标
完成最后一个数据源 `BaoStock` 的迁移，完善 API 网关的路由逻辑，并清理旧代码。

## 成功标准 (Acceptance Criteria)
1.  [x] `baostock-source` 独立运行，使用 Squid 代理访问数据。
2.  [x] `data-api` 实现完整的服务发现和降级路由 (Provider Chain over gRPC)。
3.  [x] 旧的 `data_sources/providers` 代码已从 `data-api` 中移除。
4.  [x] 系统整体通过回归测试，所有功能与重构前一致。

## 任务拆解

### 1. BaoStock 服务迁移
- [x] 创建 `services/baostock-source`
- [x] 迁移 `BaostockProvider`
- [x] 配置 Squid 代理 (`http://192.168.151.18:3128`)

### 2. 网关逻辑完善
- [x] 升级 `DataSourceGateway`
    - [x] 实现 `ProviderChain` 逻辑 (gRPC 版)
    - [x] 实现 `CircuitBreaker` (针对 gRPC 错误码)
    - [x] 实现数据源自动优选策略 (基于优先级配置)
    - [x] 集成到 main.py (启动/关闭逻辑)
    - [x] 创建监控路由 (stats/health/circuit-breaker)
    - [ ] Nacos 服务发现 (预留接口，可选)

### 3. 清理与收尾
- [x] 移除旧的 Provider 代码
- [x] 统一日志配置
- [x] 更新 `README.md` 和架构文档

### 4. 最终验证
- [x] 执行全量集成测试
- [x] 验证数据一致性 (对比新旧接口返回结果)
