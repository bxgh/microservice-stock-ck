# TDX 连接池诊断工具说明

本文档介绍了用于验证和探测 TDX 节点可用性的诊断工具。由于集群环境（Server 111）存在严格的上层防火墙策略，这些工具对于维护稳定的数据采集至关重要。

## 🛠️ 工具位置
所有诊断脚本均位于：
`services/mootdx-api/diagnostics/`

## 📋 核心工具集

### 1. `neighbor_scan_v2.py` (推荐)
**用途**：在已验证可用的网段（如海通 175.6.5.*）进行邻居扫描，自动发现新的集群节点。
**执行**：
```bash
docker exec microservice-stock-mootdx-api python /app/diagnostics/neighbor_scan_v2.py
```

### 2. `serial_test_v2.py`
**用途**：对高概率可用的 IP 列表进行串行测试（避免并发过高被防火墙暂时封锁），验证协议握手和数据返回。
**执行**：
```bash
docker exec microservice-stock-mootdx-api python /app/diagnostics/serial_test_v2.py
```

### 3. `iface_test.py`
**用途**：测试不同物理网卡（ens32, ens35）对特定 TDX 节点的连通性差异，验证策略路由是否生效。

### 4. `mass_tcp_scan.py`
**用途**：大规模扫描 140+ 个潜在节点，初步检测 TCP 端口（7709）存活情况。

---

## 🔬 诊断逻辑
1. **TCP 存活检测**：首先验证 7709 端口是否响应。
2. **协议握手验证**：通过 `mootdx.Quotes.factory` 尝试建立连接。如果返回 `Connection Reset`，说明触发了上层 DPI 拦截。
3. **数据有效性校验**：尝试获取 `get_security_count` 或个股行情，确保链路不仅通畅且能正常下发数据。

## ⚠️ 注意事项
- **绑定 IP**：大多数脚本默认读取环境变量 `TDX_BIND_IP` (192.168.151.111)，确保流量从 `ens32` 发出。
- **并发控制**：扫描时建议使用信号量（Semaphore）控制并发数，过高的瞬时连接可能导致网关触发短时封禁。
- **结果更新**：扫描出的新可用节点应及时记录到 `docs/architecture/infrastructure/VERIFIED_TDX_HOSTS_20260111.md` 中。
