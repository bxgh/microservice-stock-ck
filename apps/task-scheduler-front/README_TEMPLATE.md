# Frontend Template Framework

> 企业级前端模板框架 - 基于 Vue 3 + TypeScript + Element Plus

## 🚀 项目介绍

这是一个功能完整的企业级前端模板框架，旨在为快速开发高质量Web应用提供坚实的基础。

**🎯 设计目标：**
- 🏗️ **现代化架构** - 基于 Vue 3 + TypeScript + Vite
- 🧩 **组件化设计** - 丰富的可复用组件库
- 📚 **文档完善** - 详细的开发指南和API文档
- 🛠️ **工具链完整** - 开发、测试、构建、部署一体化
- 🎨 **设计系统** - 统一的视觉和交互规范

## 🛠️ 技术栈

### **核心框架**
- **Vue 3.4+** - 使用 Composition API
- **TypeScript 5.0+** - 类型安全开发
- **Vite 5.0+** - 极速构建工具
- **Vue Router 4** - 官方路由管理
- **Pinia 2.x** - 现代化状态管理

### **UI 组件库**
- **Element Plus** - 企业级UI组件库
- **Element Plus Icons** - 图标库

### **开发工具**
- **ESLint** - 代码质量检查
- **Prettier** - 代码格式化
- **Husky** - Git 钩子
- **Lint-staged** - 暂存文件检查
- **Vitest** - 单元测试框架

### **构建和部署**
- **Sass/SCSS** - CSS 预处理器
- **Auto Import** - 自动导入
- **Component Auto Import** - 组件自动导入

## 📦 快速开始

### **1. 安装依赖**
```bash
npm install
# 或
yarn install
```

### **2. 启动开发服务器**
```bash
npm run dev
# 或
yarn dev
```

应用将在 http://localhost:3001 启动

### **3. 构建生产版本**
```bash
npm run build
# 或
yarn build
```

### **4. 预览生产版本**
```bash
npm run preview
# 或
yarn preview
```

## 📁 项目结构

```
src/
├── 📁 components/              # 组件库
│   ├── 📁 basic/              # 基础组件
│   ├── 📁 layout/             # 布局组件
│   ├── 📁 business/           # 业务组件
│   └── 📁 charts/             # 图表组件
├── 📁 composables/           # 组合式API
├── 📁 hooks/                 # 自定义Hooks
├── 📁 utils/                 # 工具函数
├── 📁 stores/                # 状态管理
├── 📁 router/                # 路由配置
├── 📁 styles/                # 样式系统
├── 📁 views/                 # 页面组件
├── 📁 types/                 # TypeScript类型
└── 📁 assets/                # 静态资源
```

## 🎨 组件库

### **基础组件**
- `BasicButton` - 增强的按钮组件
- `BasicCard` - 增强的卡片组件
- `BasicInput` - 输入框组件
- `BasicSelect` - 选择器组件

### **布局组件**
- `AppLayout` - 应用布局
- `PageHeader` - 页面头部
- `Sidebar` - 侧边栏
- `Breadcrumb` - 面包屑导航

### **业务组件**
- `DataTable` - 数据表格
- `SearchForm` - 搜索表单
- `StatusTag` - 状态标签
- `ActionButtons` - 操作按钮组

## 🔧 开发指南

### **代码规范**
- 使用 TypeScript 进行类型检查
- 遵循 ESLint 规则
- 使用 Prettier 格式化代码
- 组件使用 PascalCase 命名
- 文件使用 kebab-case 命名

### **提交规范**
遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```bash
# 功能添加
git commit -m "feat: 添加用户登录功能"

# 问题修复
git commit -m "fix: 修复表格排序问题"

# 文档更新
git commit -m "docs: 更新组件文档"
```

### **组件开发**
1. 在 `src/components/` 对应目录创建组件
2. 使用 `<script setup>` 语法
3. 添加 TypeScript 类型定义
4. 编写组件文档和示例

## 📚 可用脚本

```bash
# 开发
npm run dev              # 启动开发服务器
npm run build            # 构建生产版本
npm run preview          # 预览生产版本

# 测试
npm run test             # 运行测试
npm run test:ui          # 运行测试UI
npm run test:coverage    # 生成覆盖率报告

# 代码质量
npm run lint             # 检查并修复代码
npm run lint:check        # 仅检查代码
npm run format           # 格式化代码
npm run format:check     # 检查格式

# 类型检查
npm run type-check       # TypeScript类型检查

# 文档
npm run docs:dev         # 启动文档开发服务器
npm run docs:build       # 构建文档
```

## 🎯 使用场景

### **1. 新项目模板**
```bash
# 克隆模板
git clone <template-url> my-project
cd my-project

# 安装依赖
npm install

# 开始开发
npm run dev
```

### **2. 组件开发**
```bash
# 创建组件
touch src/components/basic/MyComponent.vue

# 编写组件
# - 使用 Composition API
# - 添加 TypeScript 类型
# - 编写组件文档

# 导出组件
export { default as MyComponent } from './MyComponent.vue'
```

### **3. 页面开发**
```bash
# 创建页面
mkdir src/views/my-page
touch src/views/my-page/index.vue

# 配置路由
# 在 src/router/index.ts 中添加路由
```

## 🔧 配置说明

### **Vite 配置**
- 路径别名配置
- 自动导入配置
- 构建优化配置

### **TypeScript 配置**
- 严格类型检查
- 路径映射配置
- Vue 单文件组件支持

### **ESLint 配置**
- Vue 3 规则
- TypeScript 规则
- 代码风格规则

## 🤝 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Element Plus](https://element-plus.org/) - Vue 3 UI 组件库
- [TypeScript](https://www.typescriptlang.org/) - JavaScript 的超集
- [Vite](https://vitejs.dev/) - 下一代前端构建工具

---

**开发团队**: Frontend Template Team
**最后更新**: 2025-11-12