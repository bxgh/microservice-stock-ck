# 📊 Grafana 监控面板一键配置指南

这份文档旨在帮助您在 **Windows 本地 Chrome** 环境下，通过 AI 助手或手动快速构建监控大屏。

---

## 🔐 基础信息

- **Grafana URL**: `https://ac1626285367.grafana.net/`
- **数据源名称**: `TencentCloud_MySQL` (如果还没建，请先建立)
- **目标数据库**: `monitoring`

---

## 🛠️ 面板配置清单

建议创建一个名为 **"Microservice Infrastructure Health"** 的 Dashboard，并添加以下面板：

### 1. Redis 内存使用率 (Gauge)
- **标题**: `Redis Memory Usage (%)`
- **可视化类型**: `Gauge` (仪表盘)
- **SQL 查询**:
  ```sql
  SELECT 
    timestamp AS time, 
    memory_usage_percent AS value 
  FROM redis_status 
  WHERE $__timeFilter(timestamp) 
  ORDER BY timestamp
  ```
- **阈值建议**: 80% (Yellow), 90% (Red)

### 2. ClickHouse 复制延迟 (Time Series)
- **标题**: `ClickHouse Replication Lag (s)`
- **可视化类型**: `Time Series` (折线图)
- **SQL 查询**:
  ```sql
  SELECT 
    timestamp AS time, 
    absolute_delay AS value, 
    CONCAT(database_name, '.', table_name) AS metric 
  FROM clickhouse_replication 
  WHERE $__timeFilter(timestamp) 
  ORDER BY timestamp
  ```

### 3. 系统资源：CPU & 内存 (Time Series)
- **标题**: `System Resource Usage`
- **可视化类型**: `Time Series`
- **SQL 查询**:
  ```sql
  SELECT 
    timestamp AS time, 
    cpu_usage_percent AS 'CPU %',
    (memory_used_gb / memory_total_gb * 100) AS 'RAM %'
  FROM system_resources 
  WHERE server = 'server41' AND $__timeFilter(timestamp) 
  ORDER BY timestamp
  ```

### 4. GOST 隧道健康状态 (State Timeline)
- **标题**: `GOST Tunnel Status`
- **可视化类型**: `State timeline` (状态时间线)
- **SQL 查询**:
  ```sql
  SELECT 
    timestamp AS time, 
    is_healthy AS value, 
    tunnel_name AS metric 
  FROM gost_tunnel_status 
  WHERE $__timeFilter(timestamp) 
  ORDER BY timestamp
  ```
- **映射**: `1` -> `OK` (Green), `0` -> `Down` (Red)

---

## 🤖 给 Windows AI 助手的指令 (您可以直接复制这段话)

> "请帮我登录 Grafana Cloud (ac1626285367.grafana.net)，创建一个名为 'Infrastructure' 的 Dashboard。
> 
> 请连接到 MySQL 数据源，并使用以下 SQL 创建四个面板：
> 1. Redis 内存: 从 redis_status 表查 memory_usage_percent。
> 2. CH 延迟: 从 clickhouse_replication 表查 absolute_delay。
> 3. 系统资源: 从 system_resources 表查 CPU 和内存占比。
> 4. GOST 状态: 从 gost_tunnel_status 表查 is_healthy。
> 
> 数据库名为 monitoring，查询需带上 $__timeFilter(timestamp)。完成后保存并给我截图。"

---
*Created by AI Agent - 2026-01-05*
