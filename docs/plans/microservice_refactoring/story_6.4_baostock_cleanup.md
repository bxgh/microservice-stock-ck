# Story 6.4: BaoStock Logic & Cleanup

## 目标
完成最后一个数据源 `BaoStock` 的迁移，完善 API 网关的路由逻辑，并清理旧代码。

## 成功标准 (Acceptance Criteria)
1.  [ ] `baostock-source` 独立运行，使用 Squid 代理访问数据。
2.  [ ] `data-api` 实现完整的服务发现和降级路由 (Provider Chain over gRPC)。
3.  [ ] 旧的 `data_sources/providers` 代码已从 `data-api` 中移除。
4.  [ ] 系统整体通过回归测试，所有功能与重构前一致。

## 任务拆解

### 1. BaoStock 服务迁移
- [ ] 创建 `services/baostock-source`
- [ ] 迁移 `BaostockProvider`
- [ ] 配置 Squid 代理 (`http://192.168.151.18:3128`)

### 2. 网关逻辑完善
- [ ] 升级 `DataSourceGateway`
    - 实现 `ProviderChain` 逻辑 (gRPC 版)
    - 实现 `CircuitBreaker` (针对 gRPC 错误码)
    - 实现数据源自动优选策略

### 3. 清理与收尾
- [ ] 移除旧的 Provider 代码
- [ ] 统一日志配置
- [ ] 更新 `README.md` 和架构文档

### 4. 最终验证
- [ ] 执行全量集成测试
- [ ] 验证数据一致性 (对比新旧接口返回结果)
