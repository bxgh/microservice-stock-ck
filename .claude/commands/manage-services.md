# 微服务管理命令

统一管理所有微服务的状态、配置和操作。

## 命令

```bash
# 查看所有服务状态
/manage-services

# 查看特定服务
/manage-services stock-data

# 启动所有服务
/manage-services start-all

# 停止所有服务
/manage-services stop-all

# 查看服务日志
/manage-services logs task-scheduler

# 检查服务健康状态
/manage-services health
```

## 功能模块

### 1. 服务概览
显示所有微服务的状态：
```
🏗️  微服务项目概览
==================

📊 服务状态:
✅ stock-data      (模板)     - Port: 8081  - Branch: templates
🔄 task-scheduler  (开发中)   - Port: 8080  - Branch: develop
❌ api-gateway     (未启动)   - Port: 8082  - Branch: -
❌ data-collector  (未配置)   - Port: -     - Branch: -
❌ data-processor  (未配置)   - Port: -     - Branch: -
❌ data-storage    (未配置)   - Port: -     - Branch: -
❌ monitor         (未配置)   - Port: -     - Branch: -
❌ notification    (未配置)   - Port: -     - Branch: -
❌ web-ui          (未配置)   - Port: -     - Branch: -

🌿 Git 状态:
Current Branch: develop
Last Commit: docs: add project README (fdbb6f2)
Uncommitted Changes: 0
```

### 2. 服务详情
显示单个服务的详细信息：
```
📋 服务详情: task-scheduler
==========================

🏷️ 基本信息:
- 名称: task-scheduler
- 状态: 🟡 running (healthy)
- 端口: 8080
- 版本: 1.0.0-alpha

🔧 配置信息:
- Docker Compose: ✅ 已配置
- 环境变量: ✅ 已配置
- 健康检查: ✅ /api/v1/health
- 服务发现: ✅ Nacos

📊 运行状态:
- 容器状态: Up 2 hours
- 内存使用: 128MB
- CPU 使用: 2.5%
- 最后检查: 2024-01-15 10:30:00

🌿 Git 信息:
- 分支: develop
- 最后提交: feat: add task-scheduler microservice (df9b1f2)
- 未提交更改: 3 files

📚 快速操作:
- 查看日志: /manage-services logs task-scheduler
- 重启服务: /manage-services restart task-scheduler
- 查看API: http://localhost:8080/docs
```

### 3. 批量操作
一键管理多个服务：
```bash
# 启动所有配置完成的服务
/manage-services start-all

# 停止所有运行中的服务
/manage-services stop-all

# 重启特定服务
/manage-services restart task-scheduler

# 更新所有服务镜像
/manage-services update-all

# 清理未使用的资源
/manage-services cleanup
```

### 4. 健康检查
检查所有服务的健康状态：
```
🏥 服务健康检查
================

✅ stock-data:     healthy (200 OK)
✅ task-scheduler: healthy (200 OK)
❌ api-gateway:    unhealthy (connection refused)
⚠️  monitor:       warning (slow response)

📊 总体状态: 2/4 services healthy

🔧 建议操作:
- 修复 api-gateway 连接问题
- 检查 monitor 服务性能
```

### 5. 日志管理
统一查看和管理日志：
```bash
# 查看实时日志
/manage-services logs task-scheduler

# 查看最近日志
/manage-services logs task-scheduler --tail 100

# 查看错误日志
/manage-services logs task-scheduler --level error

# 查看所有服务日志
/manage-services logs --all
```

## 服务配置管理

### 端口分配
自动管理服务端口避免冲突：
```
📋 端口分配表:
- stock-data:     8081
- task-scheduler: 8080
- api-gateway:    8082
- data-collector: 8083
- data-processor: 8084
- data-storage:   8085
- monitor:        8086
- notification:   8087
- web-ui:         3000
```

### 环境变量管理
```bash
# 查看环境变量
/manage-services env task-scheduler

# 更新环境变量
/manage-services env task-scheduler set DEBUG=true

# 验证环境配置
/manage-services env check
```

### 依赖管理
```bash
# 检查服务依赖
/manage-services dependencies task-scheduler

# 检查服务间连接
/manage-services check-connections

# 验证基础设施状态
/manage-services infra-status
```

## 开发工作流集成

### 快速开发命令
```bash
# 启动开发环境
/manage-services dev-start

# 运行测试
/manage-services test task-scheduler

# 构建服务
/manage-services build stock-data

# 部署到开发环境
/manage-services deploy-dev task-scheduler
```

### Git 工作流集成
```bash
# 检查 Git 状态
/manage-services git-status

# 提交服务更改
/manage-services git-commit task-scheduler

# 合并功能分支
/manage-services git-merge feature/user-service
```

## 故障排除

### 常见问题诊断
```bash
# 诊断服务问题
/manage-services diagnose task-scheduler

# 检查网络连接
/manage-services check-network

# 验证配置文件
/manage-services validate-config
```

### 性能监控
```bash
# 查看资源使用
/manage-services stats

# 性能报告
/manage-services performance-report

# 瓶颈分析
/manage-services bottleneck-analysis
```

这个命令让微服务管理变得简单高效，一个命令就能掌握整个系统的状态！