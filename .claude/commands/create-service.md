# 创建新微服务命令

基于 stock-data 模板一键创建新的微服务，包含完整的初始化流程。

## 命令

```bash
# 使用示例
/create-service user-management
/create-service order-service
/create-service notification-service
```

## 执行流程

### 1. 验证和准备
- 检查服务名称是否合法
- 确保在正确的 Git 分支
- 验证模板是否存在

### 2. 创建服务结构
```bash
# 切换到 templates 分支
git checkout templates

# 复制模板
cp -r stock-data service-name

# 创建功能分支
git checkout -b feature/service-name
```

### 3. 自定义配置
- 更新 Docker 配置
- 修改环境变量
- 更新应用名称和端口
- 重命名示例文件

### 4. 初始化 Git
- 添加新服务到版本控制
- 创建初始提交
- 提供下一步操作指导

## 自动化修改内容

### 配置文件更新
- `.env` - 服务名称和端口
- `Dockerfile` - 应用标识
- `docker-compose.yml` - 服务配置
- `requirements.txt` - 依赖管理

### 代码文件更新
- `src/main.py` - 应用标题和描述
- `src/config/settings.py` - 配置类名
- `src/api/example_routes.py` - 路由前缀
- `README.md` - 服务文档

### 示例文件清理
- 移除模板特定的示例代码
- 清理注释中的模板引用
- 更新 API 文档示例

## 使用指南

### 服务命名规范
推荐使用 kebab-case 格式：
```
user-management     # 用户管理服务
order-processing    # 订单处理服务
payment-gateway     # 支付网关服务
data-analytics      # 数据分析服务
notification-service # 通知服务
```

### 端口分配策略
自动分配端口避免冲突：
- user-management: 8082
- order-service: 8083
- payment-gateway: 8084
- notification-service: 8085
- 以此类推...

### 后续操作
创建完成后，建议按以下步骤开发：

1. **配置数据库连接**：
   ```bash
   cd service-name
   # 编辑 .env 文件添加数据库配置
   ```

2. **实现业务逻辑**：
   ```bash
   # 修改 src/api/example_routes.py
   # 创建具体的业务路由
   ```

3. **添加依赖包**：
   ```bash
   # 更新 requirements.txt
   pip install -r requirements.txt
   ```

4. **测试服务**：
   ```bash
   docker-compose up --build
   curl http://localhost:8082/api/v1/health
   ```

## 示例输出

```
✅ 成功创建微服务: user-management

📁 服务目录: /home/bxgh/microservice-stock/services/user-management
🌿 Git 分支: feature/user-management
🔌 服务端口: 8082

📋 下一步操作:
1. cd user-management
2. 编辑 .env 文件配置数据库连接
3. 修改 src/api/example_routes.py 实现业务逻辑
4. 运行 docker-compose up --build 启动服务
5. 访问 http://localhost:8082/docs 查看API文档

🔧 快速命令:
cd user-management && docker-compose up --build

📚 更多帮助:
- 查看 GIT_WORKFLOW.md 了解开发流程
- 查看 stock-data/README.md 了解模板使用
```

## 注意事项

1. **端口冲突**：如果端口被占用，需要手动修改配置
2. **服务名称**：避免使用已存在的服务名称
3. **Git 状态**：确保当前没有未提交的更改
4. **权限问题**：确保有足够的文件操作权限

## 错误处理

- **服务已存在**：提示选择其他名称
- **Git 冲突**：提示先提交或暂存更改
- **权限不足**：提示检查文件权限
- **模板缺失**：提示检查 stock-data 目录

这个命令让创建新微服务变得像创建新文件一样简单！