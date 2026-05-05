# Story 6.5: Pywencai Logic & Integration

## 目标
创建独立的 `pywencai-source` 微服务，完成 EPIC-006 数据源微服务化的最后一块拼图。

## 成功标准 (Acceptance Criteria)
1.  [ ] `pywencai-source` 独立运行，支持 Node.js 环境。
2.  [ ] 实现 gRPC 接口，支持 SCREENING、RANKING、SECTOR 数据类型。
3.  [ ] `data-api` 集成 pywencai-source 到 DataSourceGateway。
4.  [ ] 自然语言查询功能验证通过（如"今日涨停股票"）。

## 任务拆解

### 1. Pywencai 服务创建
- [ ] 创建 `services/pywencai-source` 目录结构
- [ ] 编写 Dockerfile (含 Node.js 环境)
- [ ] 迁移 PywencaiProvider 逻辑到 gRPC Service

### 2. gRPC 接口实现
- [ ] 实现 `FetchData` RPC (支持自然语言查询)
- [ ] 实现 `HealthCheck` RPC
- [ ] 实现 `GetCapabilities` RPC
- [ ] 缓存机制集成

### 3. Gateway 集成
- [ ] 更新 `DataSourceGateway` 配置
- [ ] 添加 pywencai-source 到 ProviderChain
- [ ] 配置数据类型路由策略

### 4. 部署与验证
- [ ] 配置 Docker Compose
- [ ] 启动服务并测试健康检查
- [ ] 验证自然语言查询功能
- [ ] 性能测试（延迟 < 15s）

## 技术要点

### Node.js 环境
- 需要在 Docker 中安装 Node.js v16+
- pywencai 依赖 Node.js 执行环境

### 数据类型支持
- **SCREENING** (选股) - pywencai 独有能力
- **RANKING** (榜单) - 作为 akshare 的备选
- **SECTOR** (板块) - pywencai 优先

### 性能特征
- 查询较慢（5-15秒）
- 需要较长超时配置
- 启用缓存优化性能

## 风险
- 验证码可能导致查询失败 → 实现降级机制
- Node.js 增加镜像体积 → 使用 slim 镜像
- 查询延迟较高 → 设置合理超时和缓存
