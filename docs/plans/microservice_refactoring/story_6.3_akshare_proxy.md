# Story 6.3: AkShare Service Extraction (Explicit Proxy)

## 目标
分离依赖远程 API 的 `AkShare` 数据源，配置独立的显式 HTTP 代理环境，解决透明代理带来的稳定性问题。

## 成功标准 (Acceptance Criteria)
1.  [ ] `akshare-source` 服务独立运行，并配置了 `HTTP_PROXY` 环境变量。
2.  [ ] 能够通过代理稳定访问部署在腾讯云的 AkShare API (`124.221.80.250`)。
3.  [ ] 财务数据 (Finance) 和排行榜 (Ranking) 接口调用正常。
4.  [ ] 解决了原架构中 AkShare 偶发的连接超时问题。

## 任务拆解

### 1. 服务框架搭建
- [ ] 创建 `services/akshare-source`
    - 复用 gRPC Server 框架
    - `Dockerfile`: 重点配置环境变量支持

### 2. 远程客户端迁移
- [ ] 迁移 `AkshareProvider` (Remote API Client)
    - 确保 `aiohttp` 请求使用显式代理配置
    - 移除对本地透明代理的任何隐式依赖

### 3. gRPC 接口实现
- [ ] 实现 `FetchData` 逻辑分支
    - `RANKING`: 调用远程 API 获取榜单
    - `FINANCE`: 调用远程 API 获取报表
    - `VALUATION`: 调用远程 API 获取估值

### 4. 部署配置
- [ ] 更新 `docker-compose.yml`
    - 添加 `akshare-source`
    - **关键**: 配置 `environment` -> `HTTP_PROXY=http://192.168.151.18:3128` (产线 Squid 代理)

### 5. 验证
- [ ] 验证代理连通性 (`curl -x ...`)
- [ ] 回归测试财务数据抓取流程
