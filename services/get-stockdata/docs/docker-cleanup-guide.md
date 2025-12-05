# Docker 定时清理任务配置指南

## 概述

本文档提供了多种 Docker 定时清理任务的配置方法，帮助您自动管理 Docker 资源，避免磁盘空间不足的问题。

## 清理策略

### 安全清理（推荐日常使用）
- 清理已停止的容器
- 清理 7 天前的未使用镜像
- 清理未使用的网络
- **不清理数据卷**（避免丢失重要数据）

### 深度清理（周期性使用）
- 包含安全清理的所有内容
- 额外清理未使用的数据卷
- 清理构建缓存

## 配置方法

### 方法一：使用 Cron 定时任务（推荐）

1. **设置每日清理任务**
   ```bash
   # 编辑 crontab
   crontab -e

   # 添加以下行（每天凌晨2点执行）
   0 2 * * * /home/bxgh/microservice-stock/services/get-stockdata/scripts/docker-cleanup.sh
   ```

2. **设置周度深度清理**
   ```bash
   # 添加周度任务（周日凌晨3点执行深度清理）
   0 3 * * 0 /home/bxgh/microservice-stock/services/get-stockdata/scripts/docker-cleanup.sh && docker volume prune -f
   ```

### 方法二：使用 Docker Compose

1. **启动定时清理容器**
   ```bash
   docker compose -f docker-compose.cleanup.yml up -d
   ```

2. **查看定时清理日志**
   ```bash
   docker logs docker-cleanup-scheduler
   ```

### 方法三：使用 Systemd 服务

1. **安装服务文件**
   ```bash
   sudo cp docker-cleanup.service /etc/systemd/system/
   sudo cp docker-cleanup.timer /etc/systemd/system/
   ```

2. **启用和启动定时器**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable docker-cleanup.timer
   sudo systemctl start docker-cleanup.timer
   ```

3. **检查定时器状态**
   ```bash
   sudo systemctl status docker-cleanup.timer
   systemctl list-timers docker-cleanup
   ```

## 手动执行清理

### 快速清理
```bash
# 清理停止的容器
docker container prune -f

# 清理未使用的镜像
docker image prune -f

# 清理未使用的网络
docker network prune -f
```

### 深度清理
```bash
# 清理所有未使用的资源（包括卷）
docker system prune -a --volumes -f
```

### 自定义清理
```bash
# 清理超过30天的镜像
docker image prune -a -f --filter "until=720h"

# 清理构建缓存
docker builder prune -f
```

## 监控和日志

### 查看清理日志
```bash
# 查看清理脚本日志
tail -f /var/log/docker-cleanup.log

# 查看 Docker 系统空间使用
docker system df

# 查看详细空间使用情况
docker system df -v
```

### 监控磁盘使用
```bash
# 监控 Docker 目录大小
du -sh /var/lib/docker/

# 监控整体磁盘使用
df -h
```

## 安全注意事项

1. **数据卷清理谨慎操作**
   - 数据卷清理会永久删除数据
   - 确保重要数据已备份
   - 建议手动执行卷清理

2. **生产环境建议**
   - 先在测试环境验证清理脚本
   - 设置数据备份策略
   - 监控清理后的系统状态

3. **镜像保留策略**
   - 保留最近使用的镜像
   - 为关键应用设置镜像保留标签
   - 定期验证重要镜像可用性

## 故障排除

### 常见问题

1. **权限不足**
   ```bash
   # 确保用户在 docker 组中
   sudo usermod -aG docker $USER

   # 或使用 sudo 执行清理
   sudo docker system prune -f
   ```

2. **cron 任务不执行**
   ```bash
   # 检查 cron 服务状态
   sudo systemctl status cron

   # 查看 cron 日志
   sudo tail -f /var/log/cron.log
   ```

3. **Docker 服务不可用**
   ```bash
   # 检查 Docker 服务状态
   sudo systemctl status docker

   # 重启 Docker 服务
   sudo systemctl restart docker
   ```

## 定制化配置

### 修改清理策略
编辑 `docker-cleanup.sh` 文件，根据需要调整：
- 清理频率
- 镜像保留天数
- 日志记录方式
- 通知方式

### 添加清理规则
```bash
# 清理特定标签的镜像
docker rmi $(docker images -f "dangling=true" -q)

# 清理特定时间范围的容器
docker container prune --filter "until=24h"
```

## 最佳实践

1. **定期监控清理效果**
2. **设置合理的清理频率**
3. **保护重要数据**
4. **记录清理活动**
5. **测试清理脚本**
6. **备份关键配置**

## 联系支持

如遇问题，请检查：
- 系统日志
- Docker 日志
- 清理脚本日志
- 磁盘空间使用情况