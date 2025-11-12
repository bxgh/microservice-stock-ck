# Task Scheduler Frontend

> 基于 Vue 3 + TypeScript + Element Plus 的任务调度管理前端应用

## 🚀 项目介绍

这是 Task Scheduler 微服务的独立前端应用，提供企业级的任务调度管理界面。

**主要功能:**
- 📊 任务状态监控和统计
- ⏰ 任务调度配置和管理
- 📈 执行历史和性能分析
- 🔧 系统监控和健康检查
- 👥 用户权限和系统设置

## 🛠️ 技术栈

- **框架**: Vue 3.4+ with Composition API
- **语言**: TypeScript 5.0+
- **构建工具**: Vite 5.0+
- **UI库**: Element Plus
- **状态管理**: Pinia 2.x
- **路由**: Vue Router 4
- **HTTP客户端**: Axios
- **图表**: ECharts + Vue-ECharts
- **测试**: Vitest + Cypress

## 📦 环境要求

- Node.js >= 18.0.0
- npm >= 9.0.0 或 yarn >= 1.22.0
- Git

## 🚀 快速开始

### 1. 安装依赖
```bash
npm install
# 或
yarn install
```

### 2. 启动开发服务器
```bash
npm run dev
# 或
yarn dev
```

应用将在 http://localhost:3000 启动

### 3. 构建生产版本
```bash
npm run build
# 或
yarn build
```

### 4. 预览生产版本
```bash
npm run preview
# 或
yarn preview
```

## 📁 项目结构

详见 [设计文档](./DESIGN_PROPOSAL.md#-项目目录结构)

## 🔧 开发命令

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产版本
npm run preview

# 运行测试
npm run test

# 运行测试并监听变化
npm run test:watch

# 运行 E2E 测试
npm run test:e2e

# 代码检查
npm run lint

# 代码格式化
npm run format

# 类型检查
npm run type-check
```

## 🔗 API服务

- **后端API地址**: http://localhost:8081
- **API文档**: http://localhost:8081/docs
- **健康检查**: http://localhost:8081/api/v1/health

## 📖 开发文档

- [架构设计方案](./DESIGN_PROPOSAL.md)
- [API接口文档](./docs/API.md)
- [组件开发指南](./docs/COMPONENTS.md)
- [部署指南](./docs/DEPLOYMENT.md)

## 🧪 测试

```bash
# 运行单元测试
npm run test

# 运行测试并生成覆盖率报告
npm run test:coverage

# 运行 E2E 测试
npm run test:e2e
```

## 📊 浏览器支持

- Chrome >= 87
- Firefox >= 78
- Safari >= 14
- Edge >= 88

## 🤝 贡献指南

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 支持

如果你有任何问题或建议，请通过以下方式联系：

- 📧 Email: support@task-scheduler.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-org/task-scheduler-frontend/issues)
- 📚 Wiki: [项目Wiki](https://github.com/your-org/task-scheduler-frontend/wiki)

---

**开发团队**: Task Scheduler Frontend Team
**最后更新**: 2025-11-12