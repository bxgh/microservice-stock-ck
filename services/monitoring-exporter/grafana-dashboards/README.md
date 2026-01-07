# Grafana Dashboard 模板

## 导入说明

1. 登录 [Grafana Cloud](https://ac1626285367.grafana.net/)
2. 进入 **Dashboards** → **Import**
3. 上传 JSON 文件或粘贴内容
4. 选择 MySQL 数据源 (monitoring 库)
5. 点击 **Import**

## Dashboard 列表

| 文件 | 名称 | 用途 |
| :--- | :--- | :--- |
| [overview.json](overview.json) | 系统总览 | 一屏展示系统健康度 (手机首页) |
| [storage.json](storage.json) | 存储监控 | ClickHouse/Redis 详细指标 |
| [business.json](business.json) | 业务指标 | K线同步、快照数据、服务响应 |

## 时区说明

所有查询已使用 `timestamp - INTERVAL 8 HOUR AS time` 进行时区转换，确保 Grafana Cloud 显示正确的北京时间。

## 数据源配置

- **Type**: MySQL
- **Host**: 使用 Grafana Cloud 的 MySQL connector
- **Database**: `monitoring`
- **User**: `grafana_readonly`
- **Password**: `alwaysup@monitoring`
