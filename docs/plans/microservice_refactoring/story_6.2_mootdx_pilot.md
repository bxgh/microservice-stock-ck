# Story 6.2: MooTDX Service Extraction (Pilot)

## 目标
将 `MooTDX` 数据源从单体应用中剥离，作为第一个独立微服务 `mootdx-source` 运行，验证 gRPC 通信架构的可行性。

## 成功标准 (Acceptance Criteria)
1.  [ ] `mootdx-source` 服务能够独立启动并注册到 Nacos。
2.  [ ] `mootdx-source` 能正确处理 `QUOTES` 和 `TICK` 类型的 gRPC 请求。
3.  [ ] `data-api` (原 `get-stockdata`) 能通过 gRPC 调用 `mootdx-source` 获取数据。
4.  [ ] 分笔数据获取功能正常，性能无明显下降。

## 任务拆解

### 1. 服务框架搭建
- [ ] 创建 `services/mootdx-source`
    - `src/main.py`: gRPC Server 入口
    - `src/service.py`: 实现 `DataSourceServicer`
    - `Dockerfile`: 基于 Python 3.12 Slim

### 2. 逻辑迁移
- [ ] 迁移 `MootdxProvider` 核心逻辑
    - 复制原 `providers/mootdx` 代码到新服务
    - 适配异步 gRPC 调用方式
    - 实现数据序列化 (DataFrame -> Bytes/JSON)

### 3. API 网关适配
- [ ] 在 `data-api` 中实现 `GrpcClient`
    - 支持从 Nacos 获取服务地址
    - 实现 gRPC 调用封装
- [ ] 修改 `DataSourceFactory`
    - 增加 `grpc_mootdx` 类型支持
    - 支持配置切换 (本地 Provider -> 远程 gRPC)

### 4. 部署与验证
- [ ] 更新 `docker-compose.yml`
    - 添加 `mootdx-source` 服务
    - 配置 `network_mode: host`
- [ ] 编写集成测试 `tests/integration/test_grpc_mootdx.py`
