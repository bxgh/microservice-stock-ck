# Story 8.1: 本地容器整合

**Epic**: [EPIC-008 混合数据源架构](./EPIC-008-混合架构实施.md)  
**状态**: 就绪  
**优先级**: P0 (阻塞)  
**工作量**: 3天  
**负责人**: 待定

---

## Story 描述

**作为** 系统管理员  
**我想要** 将所有本地数据源 (mootdx, easyquotation) 整合到单个容器  
**以便** 简化部署并减少运维开销

---

## 目标

1. 将 mootdx 和 easyquotation 库合并到 `mootdx-source` 容器
2. 添加用于调用云端 API 的 HTTP 客户端模块
3. 更新 gRPC 服务实现以根据 `DataType` 路由请求
4. 为云端 API 端点配置环境变量

---

## 技术设计

### 容器架构

```
mootdx-source 容器
├── gRPC Server (:50051)
├── 本地数据源
│   ├── mootdx (TCP 直连)
│   └── easyquotation (HTTP + 代理)
└── HTTP Client (aiohttp)
    ├── akshare-api 客户端
    ├── baostock-api 客户端
    └── pywencai-api 客户端
```

### 需要修改的关键文件

| 文件 | 变更 | 原因 |
|------|------|------|
| `services/mootdx-source/requirements.txt` | 添加 `easyquotation>=0.7.0`, `aiohttp` | 整合依赖 |
| `services/mootdx-source/Dockerfile` | 使用 HTTP 镜像源安装依赖 | 绕过 Squid HTTPS 阻止 |
| `services/mootdx-source/src/service.py` | 添加路由逻辑 | 路由到本地 vs 云端 |
| `docker-compose.microservices.yml` | 添加 `HTTP_PROXY`、云端 URL | 运行时配置 |

### 路由逻辑

```python
async def FetchData(self, request, context):
    if request.type in [DATA_TYPE_QUOTES, DATA_TYPE_TICK]:
        # 使用本地 mootdx (TCP 直连)
        return await self._fetch_from_mootdx(request)
    
    elif request.type == DATA_TYPE_HISTORY:
        # 调用云端 baostock-api (HTTP)
        return await self._fetch_from_cloud(
            f"{BAOSTOCK_API_URL}/api/v1/history/kline/{code}",
            params=request.params
        )
    
    # ... 其他路由逻辑
```

---

## 验收标准

### 功能性

- [ ] 单个 `mootdx-source` 容器提供所有 5种 `DataType` 枚举
- [ ] 实时行情 (DATA_TYPE_QUOTES) 使用本地 mootdx
- [ ] 历史数据 (DATA_TYPE_HISTORY) 调用云端 baostock-api
- [ ] 选股筛选 (DATA_TYPE_SECTOR) 调用云端 pywencai-api
- [ ] 环境变量配置云端 API 基础 URL

### 非功能性

- [ ] 容器构建在 < 3分钟内完成
- [ ] 实时行情延迟 < 10ms (p95)
- [ ] 健康检查端点覆盖所有嵌入的数据源
- [ ] 优雅关闭时关闭所有连接

---

## 实施步骤

1. **更新依赖**
   ```bash
   # 添加到 requirements.txt
   echo "easyquotation>=0.7.0" >> services/mootdx-source/requirements.txt
   echo "aiohttp>=3.9.0" >> services/mootdx-source/requirements.txt
   ```

2. **创建 HTTP 客户端模块**
   ```python
   # services/mootdx-source/src/cloud_client.py
   class CloudAPIClient:
       def __init__(self, base_url: str, proxy: str):
           self.session = aiohttp.ClientSession(...)
       
       async def fetch_kline(self, symbol, params):
           # 实现
   ```

3. **更新 gRPC 服务**
   - 在 `service.py` 中添加路由逻辑
   - 在 `initialize()` 中初始化 easyquotation 和 HTTP 客户端
   - 为云端 API 超时添加错误处理

4. **更新 Docker 配置**
   ```yaml
   mootdx-source:
     environment:
       - HTTP_PROXY=http://192.168.151.18:3128
       - BAOSTOCK_API_URL=http://124.221.80.250:8001
       - PYWENCAI_API_URL=http://124.221.80.250:8002
   ```

---

## 测试策略

### 单元测试

```python
# tests/test_cloud_client.py
async def test_cloud_client_timeout():
    client = CloudAPIClient(base_url="http://mock", proxy=None)
    with pytest.raises(asyncio.TimeoutError):
        await client.fetch_kline("600519", timeout=0.001)
```

### 集成测试

```python
# tests/integration/test_hybrid_service.py
async def test_fetch_quotes_from_local():
    service = MooTDXService()
    await service.initialize()
    
    request = DataRequest(type=DATA_TYPE_QUOTES, codes=["000001"])
    response = await service.FetchData(request, None)
    
    assert response.success
    assert response.source_name == "mootdx"
    assert response.latency_ms < 50
```

---

## 依赖关系

### 被阻塞
- 无 (可立即开始)

### 阻塞
- Story 8.4: 集成和验证
- 云服务开发可以并行进行

---

## 风险

| 风险 | 缓解措施 |
|------|----------|
| mootdx 和 easyquotation 之间的依赖冲突 | 在 requirements.txt 中明确固定版本 |
| HTTP 客户端初始化减慢速度 | 使用延迟初始化，首次请求时创建会话 |
| 由于代理导致 Docker 构建失败 | 使用 HTTP 镜像 (阿里云) 而不是 HTTPS (PyPI) |

---

## 完成定义

- [ ] 代码审查并批准
- [ ] 单元测试通过 (>80% 覆盖率)
- [ ] 集成测试通过
- [ ] 容器成功构建
- [ ] 手动验证: 所有 5种 DataType 返回数据
- [ ] 文档更新 (README, ADR)
