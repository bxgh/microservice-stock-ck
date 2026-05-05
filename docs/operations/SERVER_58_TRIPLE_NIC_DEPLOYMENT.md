# Server 58 三网卡配置部署指南

> **部署日期**: 2026-01-08  
> **目标服务器**: 192.168.151.58  
> **配置模式**: 三网卡物理隔离架构

---

## 📋 配置概览

### IP 地址分配

| 网卡 | IP 地址 | 用途 | Metric |
|:-----|:--------|:-----|:-------|
| `ens32` | `192.168.151.58` | 集群同步流 (ClickHouse, Keeper) | 300 |
| `ens34` | `192.168.151.55` | HTTP 采集代理流 (Squid) | 200 |
| `ens35` | `192.168.151.56` | SSH 隧道加密流 (Gost) | 100 |

### 路由策略

- **集群节点流量** (→ 41, 111) → 强制走 `ens32`
- **代理网关流量** (→ 18) → 强制走 `ens34`
- **默认出口流量** → 优先走 `ens35` (最低 Metric)

---

## 🚀 部署步骤

### 前置检查

```bash
# 1. 确认硬件已识别
ip link show | grep ens

# 预期输出应包含：ens32, ens34, ens35
```

### 执行部署

```bash
# 2. 进入项目目录
cd /home/bxgh/microservice-stock

# 3. 执行部署脚本（需要 sudo 权限）
./deploy-triple-nic.sh
```

**⚠️ 注意事项**：
- 部署过程中可能会短暂断网（1-3秒）
- 如果通过 SSH 连接，建议在本地终端执行
- 部署前会自动备份现有配置到 `/etc/netplan/50-cloud-init.yaml.bak.YYYYMMDD_HHMMSS`

---

## ✅ 验证配置

### 自动验证

```bash
# 运行验证脚本
./verify-triple-nic.sh
```

### 手动验证

```bash
# 1. 检查网卡状态（应全部为 UP）
ip addr show ens32
ip addr show ens34
ip addr show ens35

# 2. 检查路由表
ip route show

# 预期输出应包含：
# - default via 192.168.151.254 dev ens35 proto static metric 100
# - default via 192.168.151.254 dev ens34 proto static metric 200
# - default via 192.168.151.254 dev ens32 proto static metric 300
# - 192.168.151.41 via 192.168.151.254 dev ens32 proto static metric 100
# - 192.168.151.111 via 192.168.151.254 dev ens32 proto static metric 100
# - 192.168.151.18 via 192.168.151.254 dev ens34 proto static metric 100

# 3. 测试连通性
ping -c 3 192.168.151.41   # Server 41
ping -c 3 192.168.151.111  # Server 111
ping -c 3 192.168.151.18   # 代理网关
```

---

## 🔧 故障排查

### 问题 1: 网卡未激活 (状态为 DOWN)

```bash
# 手动激活网卡
sudo ip link set ens34 up
sudo ip link set ens35 up

# 重新应用配置
sudo netplan apply
```

### 问题 2: IP 地址未分配

```bash
# 检查 Netplan 配置语法
sudo netplan generate

# 如果有错误，检查配置文件
sudo cat /etc/netplan/60-triple-nic-config.yaml

# 重新应用
sudo netplan apply
```

### 问题 3: 路由未生效

```bash
# 清除路由缓存
sudo ip route flush cache

# 重启网络服务
sudo systemctl restart systemd-networkd
```

---

## 🔄 回滚方案

如果配置出现问题，可以快速回滚：

```bash
# 1. 删除新配置
sudo rm /etc/netplan/60-triple-nic-config.yaml

# 2. 恢复备份（替换为实际备份文件名）
sudo cp /etc/netplan/50-cloud-init.yaml.bak.YYYYMMDD_HHMMSS /etc/netplan/50-cloud-init.yaml

# 3. 应用配置
sudo netplan apply
```

---

## 📊 后续优化建议

### 1. 流量监控

```bash
# 实时监控各网卡流量
watch -n 1 'ip -s link show ens32; ip -s link show ens34; ip -s link show ens35'
```

### 2. 性能测试

- 使用 `iperf3` 测试各网卡带宽
- 监控 ClickHouse 同步延迟（应 < 1ms）
- 验证 HTTP 代理流量是否正确走 `ens34`

### 3. 集群同步验证

```bash
# 在 Server 58 上测试 ClickHouse 连接
docker exec -it clickhouse-server clickhouse-client --query "SELECT * FROM system.clusters"

# 验证 Keeper 连接
echo stat | nc 192.168.151.41 9181
echo stat | nc 192.168.151.111 9181
```

---

## 📝 相关文件

- **Netplan 配置**: `/etc/netplan/60-triple-nic-config.yaml`
- **架构文档**: `docs/architecture/infrastructure/SERVER_HARDWARE_ARCHITECTURE.md`
- **部署脚本**: `deploy-triple-nic.sh`
- **验证脚本**: `verify-triple-nic.sh`

---

## ✨ 预期效果

配置成功后，Server 58 将实现：

1. ✅ **集群流量隔离**: ClickHouse 同步和 Keeper Raft 流量独占 `ens32`
2. ✅ **代理流量隔离**: HTTP 采集流量独占 `ens34`
3. ✅ **加密流量优先**: SSH 隧道和 Gost 流量优先使用 `ens35`
4. ✅ **故障容错**: 单网卡故障不影响其他流量类型
5. ✅ **性能提升**: 消除流量竞争，降低延迟抖动

---

**部署完成后，请运行验证脚本并将结果反馈！** 🚀
