# Vue组件提交模板

专门用于Vue组件开发的Git提交命令和模板。

## 快速命令

### 新建组件
```bash
# 提交新组件
git add apps/frontend-web/src/components/[组件名称]/
git commit -m "feat(components): 新增 [组件名称] 组件

- 实现组件基础功能
- 添加TypeScript类型定义
- 支持响应式设计
- 包含基本样式
- 添加组件示例

技术细节:
- Vue 3 Composition API
- TypeScript类型支持
- Props/Emits定义
- 主题变量支持

测试情况:
- ✅ 组件渲染正常
- ✅ Props验证通过
- ✅ 事件触发正常
- ✅ 响应式适配

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 组件功能更新
```bash
# 提交组件功能更新
git add apps/frontend-web/src/components/[组件名称]/
git commit -m "feat(components): 优化 [组件名称] 组件功能

- 新增 [具体功能1]
- 改进 [具体功能2]
- 修复 [已知问题]
- 性能优化

变更影响:
- 向后兼容性: [是/否]
- 破坏性变更: [是/否]
- 需要更新文档: [是/否]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 样式和UI修复
```bash
# 提交样式修复
git add apps/frontend-web/src/components/[组件名称]/index.vue
git commit -m "style(components): 修复 [组件名称] 样式问题

- 修复响应式布局
- 调整间距和对齐
- 优化暗色主题支持
- 修复浏览器兼容性

视觉变更:
- 布局: [描述]
- 颜色: [描述]
- 动画: [描述]
- 响应式: [描述]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 组件文档更新
```bash
# 提交组件文档
git add apps/frontend-web/src/views/components/index.vue
git commit -m "docs(components): 更新组件展示页面

- 添加 [组件名称] 组件示例
- 更新API文档
- 添加使用说明
- 改进交互演示

文档内容:
- 组件介绍
- API参考
- 使用示例
- 最佳实践

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## 完整的组件开发提交流程

### 1. 创建组件文件
```bash
# 创建组件目录
mkdir -p apps/frontend-web/src/components/NewComponent

# 创建组件文件
touch apps/frontend-web/src/components/NewComponent/index.vue
touch apps/frontend-web/src/components/NewComponent/types.ts
touch apps/frontend-web/src/components/NewComponent/README.md
```

### 2. 开发组件
```bash
# 编辑组件代码...
# 实现组件逻辑...
# 添加样式和交互...
```

### 3. 更新组件导出
```bash
# 更新 components/index.ts
git add apps/frontend-web/src/components/index.ts
git commit -m "chore(components): 导出 NewComponent 组件

- 添加组件到导出列表
- 更新类型声明

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 4. 更新展示页面
```bash
# 更新组件展示
git add apps/frontend-web/src/views/components/index.vue
git commit -m "docs(components): 添加 NewComponent 组件展示

- 在组件库页面添加示例
- 添加交互演示
- 更新组件分类

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## 组件类型提交规范

### Basic基础组件
```bash
feat(components): 新增 BasicButton 组件
fix(components): 修复 BasicCard 组件样式
style(components): 优化 BasicInput 组件交互
```

### Business业务组件
```bash
feat(business): 新增 DataTable 数据表格
feat(business): 添加 SearchForm 搜索表单
fix(business): 修复 Charts 组件数据处理
```

### Layout布局组件
```bash
feat(layout): 新增 Container 容器组件
feat(layout): 添加 Sidebar 侧边栏
fix(layout): 修复 Header 组件响应式问题
```

### Chart图表组件
```bash
feat(charts): 新增 LineChart 折线图
feat(charts): 添加 PieChart 饼图
fix(charts): 修复 ECharts 数据更新问题
```

## 提交清单

在提交Vue组件时，确保包含以下检查项：

### ✅ 功能检查
- [ ] 组件功能正常工作
- [ ] Props验证和默认值正确
- [ ] Events正确触发
- [ ] Slots正确渲染
- [ ] 响应式设计适配

### ✅ 代码质量
- [ ] TypeScript类型定义完整
- [ ] 代码符合项目规范
- [ ] 组件命名符合约定
- [ ] 无控制台错误和警告
- [ ] 性能优化合理

### ✅ 样式检查
- [ ] 样式符合设计规范
- [ ] 支持亮色/暗色主题
- [ ] 响应式断点正确
- [ ] 浏览器兼容性良好
- [ ] CSS变量使用规范

### ✅ 文档更新
- [ ] 组件API文档更新
- [ ] 示例代码添加
- [ ] 使用说明完善
- [ ] 更新日志记录

### ✅ 测试验证
- [ ] 本地开发测试通过
- [ ] 不同设备测试正常
- [ ] 交互体验流畅
- [ ] 边界情况处理

## 使用建议

1. **小步提交**: 每完成一个功能点就提交，避免大而全的提交
2. **明确描述**: 提交信息要明确说明变更内容和影响
3. **及时文档**: 组件完成后立即更新文档和示例
4. **测试验证**: 提交前充分测试组件功能
5. **版本兼容**: 注意向后兼容性和破坏性变更

这套提交流程和模板帮助规范Vue组件的开发和版本管理。