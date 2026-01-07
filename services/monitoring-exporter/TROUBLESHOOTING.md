# 🔍 Troubleshooting Guide (故障排查指南)

如果监控数据在 Grafana Cloud 上没有显示，请按照以下顺序检查：

---

### 1. 检查数据同步进程
**现象**: `exporter.log` 没有更新，或者 `systemctl status` 显示 failed。
- **排查**:
  ```bash
  sudo systemctl status monitoring-exporter
  ```
- **修复**:
  ```bash
  sudo systemctl restart monitoring-exporter
  ```

### 2. 检查 GOST 隧道
**现象**: 日志报错 `pymysql.err.OperationalError: (2003, "Can't connect to MySQL server on '127.0.0.1'")`。
- **排查**:
  ```bash
  systemctl status gost-mysql-tunnel
  ```
- **修复**: 隧道挂了会导致无法连接云端数据库。检查 `/home/bxgh/microservice-stock/infrastructure/gost/` 下的证书或网络配置。

### 3. 检查云端数据库
**现象**: 脚本运行正常，但数据库表里没数据。
- **排查**:
  使用本地工具通过 36301 端口连接，执行：
  ```sql
  SELECT COUNT(*) FROM monitoring.redis_status;
  ```
- **问题**: 如果数据条数在增加，说明同步没问题，请检查 Grafana 的查询语句是否有误。

### 4. 检查 Grafana 数据源
**现象**: Grafana 测试连接失败。
- **排查**:
  1. 确认腾讯云 MySQL 的公网访问权限是否开启。
  2. 确认 `grafana_readonly` 账号密码是否正确：`alwaysup@monitoring`。
  3. 确认数据库名称是否为 `monitoring`。

---
*Created by AI Agent*
