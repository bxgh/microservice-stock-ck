# Backend Smart Commit - 后端智能提交

## 命令描述

基于Git diff快速扫描和提交后端服务代码变更，**仅分析services/和packages/目录**，避免前端代码干扰，实现秒级精准提交。

## 执行流程

### 1. 后端域扫描
- 执行 `git diff --name-only` 筛选后端变更文件
- **筛选规则**: 仅处理 `services/*` 和 `packages/*` 文件
- 跳过 `apps/*` 前端文件变更
- 快速分析变更类型：服务逻辑/共享包/基础设施

### 2. 后端变更分析
- **Python语法检查**: 仅检查Python文件的语法错误
- **API接口检查**: 验证API端点变更的兼容性
- **依赖分析**: 检查requirements.txt和包依赖变更
- **服务配置**: 检查Docker和配置文件变更

### 3. 微服务关联检查
- **服务依赖**: 分析服务间的API调用关系
- **数据流检查**: 验证数据库schema变更影响
- **配置同步**: 检查跨服务配置一致性
- **Docker编排**: 验证docker-compose服务定义

### 4. 快速验证
- **Python语法**: `python -m py_compile` 快速验证
- **导入检查**: 验证Python import语句有效性
- **配置解析**: 验证YAML/JSON配置文件格式
- **Docker语法**: 检查Dockerfile和compose文件

### 5. 精准提交
- **后域暂存**: 仅添加services/和packages/变更
- **服务分类**: 按微服务分类生成提交信息
- **影响标注**: 标注受影响的其他服务
- **部署提示**: 提供部署相关建议

## 使用方法

### 基本后端提交
```
提交后端服务代码变更
```

### 指定服务描述
```
我修改了task-scheduler服务的任务调度逻辑，请智能检查变更并提交
```

### 批量服务提交
```
我完成了多个微服务的API更新，包括data-collector和notification，请智能分析并提交
```

## 后端域扫描规则

### 变更文件筛选
```bash
# 筛选后端相关文件
git diff --name-only | grep -E "^(services/|packages/)"
```

### 服务类型识别
- **数据服务**: data-collector, data-processor, data-storage
- **业务服务**: task-scheduler, notification, monitor
- **网关服务**: api-gateway, stock-data
- **共享包**: shared, utils, types, config

### 变更优先级
1. **核心服务变更**: task-scheduler, api-gateway
2. **数据服务变更**: data-* 系列服务
3. **辅助服务变更**: monitor, notification
4. **基础设施变更**: packages/config, scripts

## 输出格式

```
⚡ 后端智能提交 - 微服务域扫描模式
=====================================

1. 后端域扫描...
   📝 后端变更: 4个服务 (0.2秒)
   🎯 变更类型: fix(task-scheduler)
   📊 跳过前端文件

2. 服务变更分析...
   ✅ Python语法: 通过 (0.1秒)
   ✅ API兼容性: 通过 (0.15秒)
   ⚠️  1个依赖更新警告

3. 微服务关联分析...
   📋 依赖服务: data-collector
   📋 API影响: 2个端点变更

4. 快速验证...
   ✅ Docker配置有效
   ✅ 服务配置解析正常

5. 生成提交信息...
   📝 fix(task-scheduler): 修复任务调度逻辑错误
   ✅ 后端代码提交成功

⚡ 后端提交完成！(总耗时: 3.1秒)
```

## 注意事项

- **前端变更忽略**: 自动忽略apps/目录的所有变更
- **服务依赖**: 注意微服务间的依赖关系变更
- **配置变更**: Docker和配置文件变更需要特别关注
- **数据库变更**: schema变更需要提供迁移脚本

## 使用建议

### 推荐使用场景
- ✅ **后端服务开发**: Python服务逻辑更新
- ✅ **API接口修改**: REST API变更和兼容性
- ✅ **微服务重构**: 服务内部架构优化
- ✅ **基础设施更新**: Docker和配置调整

### 不推荐使用场景
- ❌ **全栈变更**: 同时涉及前后端的变更
- ❌ **数据库迁移**: 复杂的数据库结构变更
- ❌ **跨域重构**: 影响多个域的架构变更

这个命令专注于后端微服务的快速智能提交，是前端提交命令的理想补充。