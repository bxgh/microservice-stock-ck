# 06 数据网关：Mootdx-API 集成与配置

## 1. 服务角色
在盘中分笔采集系统中，`mootdx-api` 充当高度并行的 **数据接入层 (Data Ingestion Layer)**。它将复杂的通达信 (TDX) 二进制协议封装为标准的 RESTful 接口，供 `intraday-tick-collector` 消费。

### 核心解耦点
*   **协议转换**: 处理 TDX 专有的 L2/L1 数据包。
*   **并发控制**: 自带连接池，防止上层高并发请求直接冲垮 TDX 服务器。
*   **IP 优选**: 自动连接预设的最快 TDX 节点。

---

## 2. 关键接口规格

### 实时分笔获取
*   **Endpoint**: `GET /api/v1/tick/{code}`
*   **参数**:
    *   `offset`: 默认 800 条，最大 10000 条。
*   **响应示例**:
    ```json
    [
      {"time": "14:55:01", "price": 10.55, "volume": 12, "type": "BUY"},
      {"time": "14:55:04", "price": 10.56, "volume": 100, "type": "SELL"}
    ]
    ```

---

## 3. 核心配置说明

### 3.1 环境变量 (Environment Variables)
这些配置在各节点的 `docker-compose.node-*.yml` 中定义：

| `TDX_POOL_SIZE` | 3 - 75 | 每个进程维护的独占 TDX 连接数，41节点建议 75 |
| `TDX_HOSTS` | (优选海通/华为云) | 核心 TDX 采集节点列表，详见 `tdx_ip.md` |
| `TDX_AUTO_DISCOVER` | `false` | 禁用自动发现，强制使用 `TDX_HOSTS` 中的验证 IP |
| `TDX_BIND_IP` | 宿主机内网 IP | 显式绑定本地网卡，优化多网卡路由 |

### 3.2 性能调优
*   **Uvicorn Workers**: 每个容器通常启动 4-8 个 worker 进程，并行处理来自 Collector 的 HTTP 请求。
*   **Monkeypatch**: 系统在启动时应用了 `socket` 补丁，配合 `Gost` 代理实现全透明的流量转换，解决部分大陆 TDX 节点的连通性问题。

---

## 4. 连接池与自愈机制 (TDX Pool & Watchdog)
`mootdx-api` 内部实现了一个带 **Watchdog 巡检** 的 `AsyncContextManager` 连接池：
1.  **健壮实例 (RobustQuotes)**: 自 v1.2 起弃用 `mootdx` 自带的 `factory` 模式，改用直连 `pytdx` 的 `RobustQuotes` 包装器。这解决了 `mootdx` 初始化过程中常见的 `bestip` 逻辑竞争和属性丢失等不稳定性问题。
2.  **借出 (Acquire)**: Handler 从池中获取空闲的客户端实例。
3.  **执行 (Execute)**: 调用 TDX 接口执行业务逻辑（通过 `to_data` 进行协议转换）。
4.  **归还 (Release)**: 请求结束后立即将连接归还池中。
5.  **巡检 (Watchdog)**: 自 v1.1 起引入后台协程，每 60 秒巡检一次空闲连接：
    *   **健康检查**: 通过 `get_security_count` 验证协议握手。
    *   **过期替换**: 发现延迟 > 2s 或连接断开的节点，自动执行热替换，确保采集不中断。
6.  **端口重用与绑定**: 结合 `SO_REUSEADDR` 和 `TDX_BIND_IP` 补丁，确保高并发下的网卡稳定性和端口可用性。

> **监控提示**: 在 `/health` 接口中可以实时观察连接池状态。

---

## 5. 常见配置故障
*   **500 报错**: 通常是 `mootdx` 内部无法连接 TDX 节点，需重启容器触发 `bestip` 重选。
*   **超时 (Timeout)**: 检查 `CONCURRENCY` 是否超过了 `TDX_POOL_SIZE * Workers` 的承载能力。
*   **数据不全**: 确认 `offset` 参数是否设为 200 以上，以覆盖高频交易股的轮询间隔。
