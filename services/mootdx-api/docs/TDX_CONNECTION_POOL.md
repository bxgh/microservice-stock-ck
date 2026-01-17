# TDX 连接池技术文档

> **版本**: v2.0  
> **更新时间**: 2026-01-17  
> **所属服务**: mootdx-api  
> **核心文件**: `src/core/tdx_pool.py`

---

## 1. 概述

TDX 连接池 (`TDXClientPool`) 是 mootdx-api 服务的核心基础设施组件，负责管理与通达信 (TDX) 行情服务器的多连接资源，实现负载均衡和并发安全。

### 1.1 设计目标

| 目标 | 说明 |
|------|------|
| 并发安全 | 确保每个 pytdx 连接同一时刻仅被一个任务使用 |
| 负载均衡 | 将请求分散到多个 TDX 服务器节点 |
| 突破限流 | 通过多节点连接突破单节点并发限制 |
| 故障恢复 | 支持连接失败后的优雅降级 |

### 1.2 架构演进

| 版本 | 架构 | 问题 |
|------|------|------|
| v1.0 | Round-Robin | 非线程安全，并发时数据混乱 |
| **v2.0** | **asyncio.Queue** | ✅ 线程安全，独占式资源管理 |

---

## 2. 核心架构

### 2.1 类结构

```python
class TDXClientPool:
    """
    TDX 多节点连接池 (Thread-Safe Queue Implementation)
    
    使用 asyncio.Queue 管理连接资源，确保每个客户端
    同一时间只能被一个任务独占使用。
    """
    
    def __init__(self, size: int = 3):
        self.size = size              # 连接池大小
        self.queue = asyncio.Queue()  # 资源池 (FIFO)
        self._lock = asyncio.Lock()   # 初始化锁
        self._initialized = False     # 初始化状态
        self._all_clients = []        # 所有客户端引用
```

### 2.2 资源流转

```
┌─────────────────────────────────────────────────────────┐
│                   asyncio.Queue                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     │
│  │ Client1 │  │ Client2 │  │ Client3 │  │ Client4 │ ... │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘     │
└─────────────────────────────────────────────────────────┘
        │                                       ▲
        │ acquire() ─────────────────┐          │
        ▼                            │          │
   ┌─────────┐                       │          │
   │ Task A  │ ── 独占使用 Client ──┘          │
   └─────────┘                                  │
        │                                       │
        └───── release() ───────────────────────┘
```

### 2.3 核心方法

#### initialize()

初始化连接池，创建多个 TDX 客户端连接。

```python
async def initialize(self) -> None:
    """
    初始化流程:
    1. 检查是否已初始化 (双重检查锁)
    2. 读取环境变量配置 (TDX_HOSTS, TDX_AUTO_DISCOVER)
    3. 创建 N 个 mootdx.Quotes 客户端
    4. 将客户端放入 Queue
    """
```

**服务器选择策略**:

| 策略 | 环境变量 | 说明 |
|------|---------|------|
| 自动发现 | `TDX_AUTO_DISCOVER=true` | 使用 mootdx 内置最佳 IP 选择 |
| 白名单 | `TDX_HOSTS=ip1:port,ip2:port` | 使用指定的服务器列表 |
| 默认 | - | 使用硬编码的默认服务器 |

#### acquire()

从池中获取一个独占客户端。

```python
async def acquire(self) -> Quotes:
    """
    从 Queue 中取出一个客户端
    - 如果 Queue 为空，会阻塞等待直到有可用客户端
    - 保证返回的客户端当前未被其他任务使用
    """
    if not self._initialized:
        await self.initialize()
    return await self.queue.get()
```

#### release()

归还客户端到池中。

```python
async def release(self, client: Quotes):
    """
    将客户端放回 Queue
    - 必须在使用完成后调用
    - 推荐使用 Context Manager 自动管理
    """
    await self.queue.put(client)
```

---

## 3. 使用方式

### 3.1 Context Manager (推荐)

```python
# MootdxHandler 中的封装
@asynccontextmanager
async def acquire_client(self):
    client = await self.pool.acquire()
    try:
        yield client
    finally:
        await self.pool.release(client)

# 使用示例
async with handler.acquire_client() as client:
    data = client.quotes(symbol="600519")
```

### 3.2 手动管理

```python
client = await pool.acquire()
try:
    data = client.quotes(symbol="600519")
finally:
    await pool.release(client)
```

---

## 4. 配置

### 4.1 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TDX_POOL_SIZE` | 3 | 连接池大小 |
| `TDX_AUTO_DISCOVER` | false | 是否自动发现最佳服务器 |
| `TDX_HOSTS` | - | 服务器列表 (逗号分隔) |
| `TDX_BIND_IP` | - | 强制绑定的源 IP |

### 4.2 推荐配置

**生产环境 (分布式采集)**:
```yaml
TDX_POOL_SIZE: 50
TDX_AUTO_DISCOVER: false
TDX_HOSTS: "175.6.5.153:7709,175.6.5.154:7709,139.9.133.247:7709"
TDX_BIND_IP: "192.168.151.111"  # 绑定特定网卡
```

**开发环境**:
```yaml
TDX_POOL_SIZE: 3
TDX_AUTO_DISCOVER: true
```

---

## 5. 网络配置

### 5.1 源 IP 绑定 (Monkey Patch)

在特殊网络环境下 (如多网卡、策略路由)，需要强制绑定源 IP：

```python
# tdx_pool.py 中的 Monkey Patch
_TDX_BIND_IP = os.getenv("TDX_BIND_IP")
if _TDX_BIND_IP:
    _OriginalSocket = socket.socket
    class _BoundSocket(_OriginalSocket):
        def connect(self, address):
            is_tdx = address[1] in [7701, 7709, 7711, 7727]
            if is_tdx:
                self.bind((_TDX_BIND_IP, 0))
            super().connect(address)
    socket.socket = _BoundSocket
```

**适用场景**:
- 多网卡服务器
- 策略路由 (Policy Routing)
- 防火墙 DPI 白名单

### 5.2 Docker 网络模式

| 模式 | 说明 | 推荐 |
|------|------|------|
| `bridge` | 默认模式，包经过 NAT | ❌ |
| `host` | 共享宿主机网络栈 | ✅ |

**原因**: Bridge 模式下源 IP 会变为 Docker 网桥 IP，导致策略路由失效。

---

## 6. 验证服务器列表

### 6.1 已验证节点 (2026-01-12)

| IP | 端口 | 运营商 | 状态 |
|----|------|--------|------|
| 175.6.5.153 | 7709 | 湖南电信 | ✅ |
| 175.6.5.154 | 7709 | 湖南电信 | ✅ |
| 175.6.5.155 | 7709 | 湖南电信 | ✅ |
| 175.6.5.156 | 7709 | 湖南电信 | ✅ |
| 139.9.133.247 | 7709 | 华为云 | ✅ |
| 139.9.51.18 | 7709 | 华为云 | ✅ |
| 139.159.239.163 | 7709 | 华为云 | ✅ |
| 119.147.212.81 | 7709 | 广东电信 | ✅ |
| 47.107.64.168 | 7709 | 阿里云 | ✅ |
| 119.29.19.242 | 7709 | 腾讯云 | ✅ |

### 6.2 端口说明

| 端口 | 用途 |
|------|------|
| 7709 | 标准行情端口 |
| 7701 | 备用端口 |
| 7711 | 备用端口 |
| 7727 | 扩展端口 |

---

## 7. 性能数据

### 7.1 测试结果 (2026-01-07)

| 配置 | 节点数 | 并发数 | 耗时 | 提速比 |
|------|--------|--------|------|--------|
| 基线 | 1 | 2 | 110 分钟 | 1.0x |
| **优化后** | 3 | 6 | **80 分钟** | **1.38x** |

### 7.2 关键指标

| 指标 | 数值 |
|------|------|
| 成功率 | 98.0% |
| 09:25 覆盖率 | 98.8% |
| 平均处理速度 | 65 股/分钟 |
| 总记录数 | 14.8M 条 |

### 7.3 提速限制因素

| 因素 | 影响 |
|------|------|
| TDX 服务器限流 | 单 IP 并发上限 |
| 网络延迟 | 跨地域访问 |
| ClickHouse 写入 | 批量写入瓶颈 |

---

## 8. 线程安全保证

### 8.1 v1.0 问题 (Round-Robin)

```python
# 危险: 多个任务可能同时使用同一个 client
client = clients[index % len(clients)]
index += 1
```

**问题**: pytdx 底层 socket 非线程安全，并发访问导致:
- 数据包混乱
- 连接重置 (Connection Reset)
- 返回错误数据

### 8.2 v2.0 解决方案 (Queue)

```python
# 安全: 每个 client 同一时刻只被一个任务使用
client = await queue.get()   # 独占获取
# ... 使用 client ...
await queue.put(client)      # 归还
```

**保证**: 
- 独占式访问
- FIFO 公平调度
- 阻塞等待机制

---

## 9. 监控与诊断

### 9.1 状态查询

```python
status = pool.get_status()
# {
#     "pool_size": 5,
#     "available": 3,
#     "initialized": true
# }
```

### 9.2 健康检查 API

```
GET /health
```

```json
{
  "pool": {
    "initialized": true,
    "size": 5,
    "available": 3
  }
}
```

### 9.3 诊断工具

| 脚本 | 用途 |
|------|------|
| `diagnostics/test_tdx_connectivity.py` | 测试 TDX 连接性 |
| `diagnostics/verify_tdx_20260112.py` | 验证绑定 IP |
| `diagnostics/mass_tdx_scan.py` | 批量扫描节点 |

---

## 10. 故障排查

### 10.1 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 连接超时 | 节点不可达 | 更换 TDX_HOSTS |
| Connection Reset | 防火墙拦截 | 设置 TDX_BIND_IP |
| 数据混乱 | 使用旧版 Round-Robin | 升级到 Queue 版本 |
| 初始化失败 | 所有节点不可用 | 检查网络/防火墙 |

### 10.2 日志关键字

```
# 成功
✓ TDX Pool Ready (5/5 available)
Node 1 conn 175.6.5.153:7709

# 失败
Pool init failed: 0 connections
Node 1 init failed: Connection timed out
```

---

## 11. 相关文档

| 文档 | 路径 |
|------|------|
| 性能测试报告 | `../../docs/reports/PERFORMANCE_TEST_TDX_POOL_20260107.md` |
| Docker 部署指南 | `../../docs/architecture/data_acquisition/TDX_POOL_DOCKER_CONFIG.md` |
| Server 41 配置 | `../../docs/architecture/data_acquisition/TDX_POOL_DOCKER_CONFIG_41.md` |
| Server 58 配置 | `../../docs/architecture/data_acquisition/TDX_POOL_DOCKER_CONFIG_58.md` |
| 验证节点列表 | `../../docs/architecture/infrastructure/VERIFIED_TDX_HOSTS_20260111.md` |
