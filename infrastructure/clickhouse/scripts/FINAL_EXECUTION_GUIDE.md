# 🚀 ClickHouse 3节点扩容 - 最终执行指南

## 📋 执行环境确认

✅ **已确认信息**:
- **Server 58**: 从41克隆，环境完全一致
- **Server 111**: 从41克隆，环境完全一致
- **部署方式**: Docker容器，配置文件路径相同
- **当前位置**: Server 41 (192.168.151.41)
- **Keeper Leader**: Server 58 (Leader), Server 41 (Follower)

---

## ⚡ 一键执行（推荐）

### 使用自动化脚本

**脚本**: [one_click_expansion.sh](file:///home/bxgh/microservice-stock/infrastructure/clickhouse/scripts/one_click_expansion.sh)

**执行命令**:
```bash
cd /home/bxgh/microservice-stock
sudo bash infrastructure/clickhouse/scripts/one_click_expansion.sh
```

### 脚本功能
- ✅ 自动备份当前配置
- ✅ 验证集群健康状态
- ✅ 测试SSH连通性
- ✅ 按正确顺序更新所有节点（41 → 111 → 58）
- ✅ 自动重启容器
- ✅ 验证3节点集群状态
- ✅ 显示详细执行结果

### 预计时间
- **总耗时**: 3-5 分钟
- **每台服务器中断**: 10-20 秒
- **用户交互**: 需要2次确认

---

## 📝 手动执行（备选方案）

如果自动化脚本遇到问题，可以手动执行：

### Step 1: 备份配置（30秒）
```bash
cd /home/bxgh/microservice-stock
mkdir -p /backup/clickhouse-expansion-$(date +%Y%m%d-%H%M%S)
cp infrastructure/clickhouse/config/*.xml /backup/clickhouse-expansion-$(date +%Y%m%d-%H%M%S)/
```

### Step 2: 更新 Server 41 配置（1分钟）
```bash
# 在 41 服务器上
cd /home/bxgh/microservice-stock

# 使用3节点配置
cp infrastructure/clickhouse/config/keeper_config_41_3nodes.xml \
   infrastructure/clickhouse/config/keeper_config.xml

cp infrastructure/clickhouse/config/replication_config_41_3nodes.xml \
   infrastructure/clickhouse/config/replication_config.xml

# 重启容器
docker restart microservice-stock-clickhouse

# 等待启动
sleep 15

# 验证
echo "mntr" | nc localhost 9181 | grep zk_server_state
```

### Step 3: 部署 Server 111 配置（1分钟）
```bash
# 从41传输配置到111
scp infrastructure/clickhouse/config/keeper_config_111.xml \
    root@192.168.151.111:/home/bxgh/microservice-stock/infrastructure/clickhouse/config/keeper_config.xml

scp infrastructure/clickhouse/config/replication_config_111.xml \
    root@192.168.151.111:/home/bxgh/microservice-stock/infrastructure/clickhouse/config/replication_config.xml

# SSH到111重启容器
ssh root@192.168.151.111 "cd /home/bxgh/microservice-stock && docker restart microservice-stock-clickhouse"

# 等待启动
sleep 15

# 验证
ssh root@192.168.151.111 "echo 'mntr' | nc localhost 9181 | grep zk_server_state"
```

### Step 4: 更新 Server 58 配置（1分钟）
```bash
# 从41传输配置到58
scp infrastructure/clickhouse/config/keeper_config_58_3nodes.xml \
    root@192.168.151.58:/home/bxgh/microservice-stock/infrastructure/clickhouse/config/keeper_config.xml

scp infrastructure/clickhouse/config/replication_config_58_3nodes.xml \
    root@192.168.151.58:/home/bxgh/microservice-stock/infrastructure/clickhouse/config/replication_config.xml

# SSH到58重启容器（Leader最后）
ssh root@192.168.151.58 "cd /home/bxgh/microservice-stock && docker restart microservice-stock-clickhouse"

# 等待启动
sleep 15

# 验证
ssh root@192.168.151.58 "echo 'mntr' | nc localhost 9181 | grep zk_server_state"
```

### Step 5: 验证3节点集群（1分钟）
```bash
# 检查副本状态
docker exec microservice-stock-clickhouse clickhouse-client --query "
SELECT 
    database, table,
    total_replicas,
    active_replicas,
    is_readonly
FROM system.replicas
LIMIT 5
FORMAT Vertical
"

# 预期结果：total_replicas = 3, active_replicas = 3
```

---

## ⏰ 建议执行时间

### 方案 A: 今晚盘后（推荐）
- **时间窗口**: 2026-01-07 15:30 - 23:00
- **当前时间**: 14:54
- **距离开始**: 约36分钟
- **优点**: 
  - 盘后时段，影响小
  - 今天完成，周三可观察
  - 时间充裕

### 方案 B: 本周末
- **时间窗口**: 2026-01-11/12 全天
- **优点**:
  - 非交易日，最安全
  - 时间充裕，可以慢慢验证
  - 发现问题有充足时间修复

---

## 🔍 执行前最后确认

### SSH密钥配置
确保从41可以免密SSH到58和111：

```bash
# 测试SSH连接
ssh root@192.168.151.58 "hostname"
ssh root@192.168.151.111 "hostname"

# 如果需要密码，配置SSH密钥:
ssh-copy-id root@192.168.151.58
ssh-copy-id root@192.168.151.111
```

### 集群状态检查
```bash
# 确认当前2节点集群健康
docker exec microservice-stock-clickhouse clickhouse-client --query "
SELECT count() as total_tables, sum(is_readonly) as readonly_tables 
FROM system.replicas
"

# 预期: total_tables > 0, readonly_tables = 0
```

---

## 🎯 执行流程总结

```
┌─────────────────────────────────────────┐
│  1. 执行一键脚本                         │
│     sudo bash one_click_expansion.sh    │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  2. 脚本自动执行8个步骤                  │
│     • 备份配置                           │
│     • 验证状态                           │
│     • 更新41 → 重启                      │
│     • 更新111 → 重启                     │
│     • 更新58 → 重启                      │
│     • 验证3节点                          │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  3. 验证结果                             │
│     • total_replicas = 3 ✅              │
│     • active_replicas = 3 ✅             │
│     • 3个Keeper节点运行 ✅               │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│  4. 完成！🎉                             │
│     真正的高可用集群就绪                 │
└─────────────────────────────────────────┘
```

---

## 📞 故障排查

### 问题1: SSH连接失败
```bash
# 解决方案: 配置SSH密钥或使用密码
ssh-copy-id root@192.168.151.58
ssh-copy-id root@192.168.151.111
```

### 问题2: 容器启动失败
```bash
# 查看日志
docker logs microservice-stock-clickhouse

# 检查配置文件语法
docker exec microservice-stock-clickhouse clickhouse-server --config-file=/etc/clickhouse-server/config.xml --test
```

### 问题3: Keeper无法形成仲裁
```bash
# 检查网络连通性
nc -zv 192.168.151.58 9234
nc -zv 192.168.151.111 9234

# 查看Keeper日志
docker logs microservice-stock-clickhouse | grep -i keeper
```

### 问题4: 副本未全部在线
```bash
# 等待5-10分钟让集群同步
# 查看同步队列
watch 'docker exec microservice-stock-clickhouse clickhouse-client --query "SELECT sum(queue_size) FROM system.replicas"'

# 队列应该逐渐降为0
```

---

## 🔄 回退方案

如果扩容失败，快速回退：

```bash
# 1. 停止111节点
ssh root@192.168.151.111 "docker stop microservice-stock-clickhouse"

# 2. 在41上恢复备份配置
cd /home/bxgh/microservice-stock
LATEST_BACKUP=$(ls -td /backup/clickhouse-expansion-* | head -1)
cp $LATEST_BACKUP/*.xml infrastructure/clickhouse/config/

# 3. 重启41和58
docker restart microservice-stock-clickhouse
ssh root@192.168.151.58 "docker restart microservice-stock-clickhouse"

# 4. 验证2节点集群恢复
docker exec microservice-stock-clickhouse clickhouse-client --query \
"SELECT * FROM system.replicas FORMAT Vertical"
```

---

## 📊 验证成功的标志

执行以下命令，所有检查都应该通过：

```bash
# 1. Keeper集群有3个节点
echo "mntr" | nc localhost 9181 | grep zk_peer
# 应显示2个peer

# 2. 复制表有3个副本
docker exec microservice-stock-clickhouse clickhouse-client --query \
"SELECT DISTINCT total_replicas FROM system.replicas"
# 应返回: 3

# 3. 所有副本在线
docker exec microservice-stock-clickhouse clickhouse-client --query \
"SELECT DISTINCT active_replicas FROM system.replicas"
# 应返回: 3

# 4. 无只读表
docker exec microservice-stock-clickhouse clickhouse-client --query \
"SELECT sum(is_readonly) FROM system.replicas"
# 应返回: 0

# 5. 可以跨节点写入和读取
# 在41上写入
docker exec microservice-stock-clickhouse clickhouse-client --query \
"INSERT INTO <某个复制表> VALUES (...)"

# 在58/111上能立即读取到
```

---

## 🎉 执行完成后

### 更新文档
- [ ] 更新架构文档，标注3节点配置
- [ ] 更新监控面板，添加111节点

### 持续监控
```bash
# 添加到cron定期检查
*/30 * * * * echo "mntr" | nc localhost 9181 | grep -E "(zk_server_state|zk_followers)" >> /var/log/keeper_health.log
```

### 负载均衡
考虑在应用层配置3个节点的轮询访问：
```yaml
clickhouse_hosts:
  - 192.168.151.41:9000
  - 192.168.151.58:9000
  - 192.168.151.111:9000  # 新增
```

---

## 📚 相关文档

- [完整扩容方案](file:///home/bxgh/microservice-stock/docs/operations/CLICKHOUSE_3NODE_EXPANSION.md) - 详细理论和风险说明
- [快速操作指南](file:///home/bxgh/microservice-stock/infrastructure/clickhouse/scripts/QUICK_START_GUIDE.md) - 简化版执行流程
- [前置检查报告](file:///home/bxgh/microservice-stock/infrastructure/clickhouse/scripts/PRE_EXPANSION_CHECK_REPORT.md) - Server 41检查结果
- [集群架构文档](file:///home/bxgh/microservice-stock/docs/architecture/clickhouse-replicated-cluster.md) - 架构说明

---

**创建时间**: 2026-01-07 14:55  
**当前状态**: ✅ 一切就绪，随时可以执行！  
**推荐执行时间**: 今晚 15:30 后或本周末

---

## 🚦 现在可以开始了！

只需执行：
```bash
cd /home/bxgh/microservice-stock
sudo bash infrastructure/clickhouse/scripts/one_click_expansion.sh
```

**祝顺利！🎉**
