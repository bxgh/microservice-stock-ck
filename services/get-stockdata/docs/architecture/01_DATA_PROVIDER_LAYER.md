# 数据源提供者层 (Data Provider Layer)

**实现路径**: `src/data_sources/`

## 1. 设计模式：Provider Pattern

为了适配多种异构数据源（TCP、HTTP API、gRPC），系统采用了统一的 `DataProvider` 接口抽象。

### 基类: `DataProvider`
定义在 `src/data_sources/base.py`。
- **统一接口**: `fetch(data_type, **kwargs)` 是主入口。
- **能力声明**: `capabilities` 返回该提供者支持的数据类型。
- **优先级**: `priority_map` 用于 Service 层决定多数据源降级顺序。

---

## 2. 核心 Provider 实现

| Provider | 代码路径 | 协议 | 关键特性 |
| :--- | :--- | :--- | :--- |
| **MootdxProvider** | `providers/mootdx_provider.py` | TCP (TDX) | **直连模式**。绕过 HTTP 代理，实现低延迟盘口和分笔获取。支持连接池管理。 |
| **AkshareProvider** | `providers/akshare_provider.py` | HTTP | **中转模式**。通过特定网关访问 AkShare API。主要用于财务指标、人气榜单。 |
| **BaostockProvider** | `providers/baostock_provider.py` | HTTP | **代理模式**。针对 Baostock 封装的云端 API，用于历史日线 K 线补全。 |
| **PywencaiProvider** | `providers/pywencai.py` | HTTP | 用于板块分析和复杂的语义选股数据。 |

---

## 3. 网络与代理策略

根据代码实现（`src/data_sources/factory.py`），Provider 的网络配置遵循以下原则：

- **TCP 直连 (Host Mode)**: Mootdx 流量不经过 Squid 代理，直接绑定宿主机网卡 (`TDX_BIND_IP`) 以确保性能。
- **HTTP 代理 (Gateway Mode)**: 云端 API 请求统一注入 `PROXY_URL` (通常为 `3128` 端口)，实现内外网隔离下的安全访问。

---

## 4. 异常处理与连接管理

- **自动重连**: `MootdxProvider` 内部实现了针对通达信连接闪断的重试逻辑。
- **资源清理**: 每个 Provider 必须实现 `close()` 方法，在应用关闭时释放 HTTP Session 或 TCP 句柄。
