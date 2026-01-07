# ✅ Server 41 前置检查完成报告

## 📊 检查总结

**检查时间**: 2026-01-07 14:50  
**当前位置**: Server 41 (192.168.151.41)  
**检查结果**: ✅ **所有关键项通过，可以进行扩容！**

---

## 🎯 关键发现

### 1. Keeper Leader 确认
- **Server 41**: 🔵 **Follower**  
- **Server 58**: 🔴 **Leader** ← 最后重启
- **重启顺序**: **41 (Follower) → 111 (New) → 58 (Leader)** ✅

### 2. ClickHouse 部署方式
- **运行方式**: Docker 容器化部署
- **容器名**: `microservice-stock-clickhouse`
- **版本**: 25.10.1.3832-stable
- **状态**: Up 38 hours (healthy) ✅

### 3. 配置文件挂载路径
```yaml
volumes:
  - ./infrastructure/clickhouse/config/keeper_config.xml:/etc/clickhouse-server/config.d/keeper_config.xml:ro
  - ./infrastructure/clickhouse/config/replication_config.xml:/etc/clickhouse-server/config.d/replication_config.xml:ro
```

**关键**: 配置文件在 `/home/bxgh/microservice-stock/infrastructure/clickhouse/config/`

### 4. 当前配置状态
- **keeper_config.xml**: ✅ 已存在，当前2节点模式（server_id=1）
- **replication_config.xml**: ✅ 已存在，replica=server41
- **3节点配置文件**: ✅ 已准备好
  - `keeper_config_41_3nodes.xml`
  - `replication_config_41_3nodes.xml`

### 5. 集群健康状况
| 指标 | 当前值 | 状态 |
|:-----|:-------|:-----|
| 复制表总数 | 14 | ✅ |
| 只读表数 | 0 | ✅ 全部可写 |
| 在线副本数 | 2/2 | ✅ 100%在线 |
| 同步队列 | 4 | ✅ 正常 |
| 磁盘使用率 | 41% | ✅ 充足 |

### 6. 网络连通性
- **到Server 58**: ✅ 所有端口 (9000/9009/9181/9234) 连通
- **到Server 111**: ✅ 所有端口 (9000/9009/9181/9234) 连通

---

## 🚀 可以立即开始扩容！

### 扩容准备工作 ✅ 完成
- [x] 前置检查完成
- [x] Keeper Leader 已确认
- [x] 3节点配置文件已准备
- [x] 网络连通性验证通过
- [x] 当前集群状态健康

### 扩容执行计划

#### 方案A: 今晚盘后执行（推荐）
**时间窗口**: 2026-01-07 15:30 - 23:00  
**风险**: 低（盘后时段，影响小）

#### 方案B: 本周末执行（最安全）
**时间窗口**: 2026-01-11/12 全天  
**风险**: 最低（非交易日，时间充裕）

---

## 📝 扩容步骤简化版（基于Docker）

### Step 1: 备份当前配置（30秒）
```bash
# 在 41 服务器上
cd /home/bxgh/microservice-stock
mkdir -p /backup/clickhouse-config-$(date +%Y%m%d-%H%M%S)
cp infrastructure/clickhouse/config/keeper_config.xml /backup/clickhouse-config-$(date +%Y%m%d-%H%M%S)/
cp infrastructure/clickhouse/config/replication_config.xml /backup/clickhouse-config-$(date +%Y%m%d-%H%M%S)/
```

### Step 2: 更新 41 服务器配置（1分钟）
```bash
# 在 41 服务器上
cd /home/bxgh/microservice-stock

# 使用已准备好的3节点配置
cp infrastructure/clickhouse/config/keeper_config_41_3nodes.xml \
   infrastructure/clickhouse/config/keeper_config.xml

cp infrastructure/clickhouse/config/replication_config_41_3nodes.xml \
   infrastructure/clickhouse/config/replication_config.xml

# 重启容器（Follower先）
docker restart microservice-stock-clickhouse

# 等待10秒
sleep 10

# 验证重启成功
docker ps | grep clickhouse
echo "mntr" | nc localhost 9181 | grep zk_server_state
```

### Step 3: 部署 111 服务器（需SSH到111）
```bash
# SSH到 111 服务器
ssh root@192.168.151.111

# 确保已复制配置文件到111
# 使用准备好的 keeper_config_111.xml 和 replication_config_111.xml

# 启动 ClickHouse（Docker或systemd方式）
# 如果是Docker方式，需要类似的docker-compose配置
```

### Step 4: 更新 58 服务器配置（需SSH到58）
```bash
# SSH到 58 服务器  
ssh root@192.168.151.58

# 更新配置（使用 keeper_config_58_3nodes.xml 和 replication_config_58_3nodes.xml）

# 重启容器（Leader最后）
docker restart <容器名>

# 验证
echo "mntr" | nc localhost 9181 | grep zk_server_state
```

### Step 5: 验证 3节点集群（2分钟）
```bash
# 在任意节点上执行
docker exec microservice-stock-clickhouse clickhouse-client --query "
SELECT 
    database, table,
    total_replicas,
    active_replicas
FROM system.replicas
LIMIT 5
FORMAT Vertical
"

# 预期结果: total_replicas = 3, active_replicas = 3
```

---

## ⚠️ 重要提醒

### Docker方式的特殊考虑
1. **配置立即生效**: 本地文件修改后，重启容器即可加载新配置
2. **无需进入容器**: 配置文件挂载为只读（`ro`），直接修改宿主机文件
3. **健康检查**: 容器会自动执行健康检查，确保服务正常

### 111服务器部署方式
需要确认111服务器上ClickHouse的部署方式：
- **选项A**: Docker方式（与41/58一致） ← 推荐
- **选项B**: 系统服务方式（systemd）

**建议**: 如果111是克隆的41，应该已经有Docker环境，使用相同部署方式最简单。

---

## 📞 需要协助的信息

请提供以下信息以完善扩容计划：

1. **111服务器确认**:
   - [ ] 111上ClickHouse是否已安装？（Docker or systemd）
   - [ ] 111上是否需要我们准备docker-compose配置？
   
2. **58服务器状态**:
   - [ ] 58是否也是Docker部署？
   - [ ] 58的配置文件路径是否与41一致？

3. **执行时间确认**:
   - [ ] 选择今晚15:30后？
   - [ ] 还是等到本周末？

---

## 🎯 当前状态
✅ **Server 41 准备就绪，随时可以开始扩容！**

**下一步**: 请确认111和58的部署方式，我将提供完整的一键扩容脚本。

---

**报告生成**: 2026-01-07 14:51  
**有效期**: 建议24小时内执行（集群状态可能变化）
