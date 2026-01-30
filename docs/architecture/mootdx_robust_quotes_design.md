# RobustQuotes 设计与实现技术文档

## 1. 背景 (Background)
在分布式盘中分笔采集系统中，`mootdx-api` 是连接 A 股通达信 (TDX) 行情源的核心网关。原系统基于 `mootdx` 官方库的 `Quotes.factory` 模式构建，但在 Server 41 节点的 75 并发连接池压力下，暴露了严重的不稳定性问题，导致分笔数据采集频繁中断。

`RobustQuotes` 是为了彻底解决这些底层稳定性问题而重新设计的 **高性能协议包装类**。

---

## 2. 核心痛点与解决方案 (Problems & Solutions)

### 2.1 异步初始化竞争 (Initialization Race Condition)
*   **问题**: `mootdx` 的 `factory` 模式在并发创建多个实例时，会并发执行 `bestip` 服务器优选逻辑。由于其内部非线程安全的设计，会导致属性丢失，产生 `AttributeError: 'TdxHq_API' object has no attribute 'api'` 报错。
*   **方案**: **绕过工厂模式**。`RobustQuotes` 直接实例化底层 `pytdx.hq.TdxHq_API`，跳过自动优选，由连接池显式指定验证过的 IP 节点，实现秒级无锁初始化。

### 2.2 连接“假成功”与空数据 (Phantom Connections)
*   **问题**: 原生库有时会返回一个看似建立的连接，但底层未完成 TDX 握手。调用 `transaction` 接口时不会报错，但始终返回空数据（Length=0），导致严重的数据丢失。
*   **方案**: **强制握手验证**。在 `RobustQuotes` 初始化过程中，直接调用 `client.connect` 并设置严格的 `time_out`，并在连接池层级配合守护协程 (Watchdog) 定时执行心跳检测。

### 2.3 多网卡选路冲突 (Multi-NIC Routing Issues)
*   **问题**: 在多网卡 (Server 41 有 3 块网卡) 环境下，OS 路由表可能导致 TDX 流量从错误的网卡流出，导致连接被防火墙拦截 (Connection Reset)。
*   **方案**: **Socket 级强绑定**。通过在 `tdx_pool.py` 中注入 `MonkeyPatch`，拦截 `socket.connect` 调用，根据 `TDX_BIND_IP` 环境变量，强行将所有 7709 端口的外部连接绑定到指定内网 IP。

---

## 3. 架构设计 (Architecture)

### 3.1 组合优于继承 (Composition vs Inheritance)
不同于早期的 `RobustQuotes(StdQuotes)` 继承方案，最终版采用了**组合 (Composition)** 模式：
*   **内部持有**: 包装类内部持有一个 `pytdx.hq.TdxHq_API` 实例。
*   **接口对齐**: 手动映射 `quotes()`, `transaction()`, `bars()` 等核心接口，确保与 `mootdx` 的 API 签名 100% 兼容。
*   **解耦**: 这种设计完全隔离了 `mootdx` 库复杂的内部逻辑，使我们可以精细控制每一次 TCP 握手。

### 3.2 数据标准化流 (Standardized Pipeline)
```text
pytdx (Raw List/Dict) -> RobustQuotes (Wrapper) -> mootdx.utils.to_data -> pandas.DataFrame
```
利用 `mootdx.utils.to_data` 工具函数，我们将底层的 C 结构化数据转换为业务层期待的高性能 `DataFrame`，同时保留了 `mootdx` 优秀的数据解析能力。

---

## 4. 关键特性 (Key Features)

*   **端口重用 (SO_REUSEADDR)**: 在 MonkeyPatch 中默认开启，防止系统产生大量 `TIME_WAIT` 连接，解决盘中高频重试导致的端口耗尽。
*   **自动资源回收**: 实现 `__del__` 和 `close()` 逻辑，确保当连接池缩容或容器关闭时，底层 TCP 连接被优雅切断，减少 TDX 服务器端的并发占用。
*   **轻量化**: 去除了所有不必要的后台线程和自动更新逻辑，将单连接内存占用降低了约 30%。

---

## 5. 接口映射参考 (API Reference)

| 业务方法 | 底层 PyTDX 接口 | 说明 |
| :--- | :--- | :--- |
| `quotes(symbol)` | `get_security_quotes` | 支持多代码批量查询快照 |
| `transaction(code)` | `get_transaction_data` | 获取当日实时分笔成交 |
| `transactions(code, date)` | `get_history_transaction_data`| 获取历史分笔成交 (追补核心) |
| `bars(freq, code)` | `get_instrument_bars` | 获取历史 K 线 |
| `finance(code)` | `get_finance_info` | 映射财务基础数据 |

---

## 6. 维护与监控
*   **日志标识**: 搜索 `tdx-pool` 或 `MonkeyPatch` 关键字。
*   **故障排查**: 若出现 `Tick count is 0`，应首先检查 `TDX_HOSTS` 中的 IP 是否被防火墙拦截，或该节点是否支持分笔数据。
*   **性能巡检**: 连接池每 60 秒会自动调用各实例的 `api` 属性进行健康检查。

---
*文档版本: v1.2*
*更新日期: 2026-01-30*
