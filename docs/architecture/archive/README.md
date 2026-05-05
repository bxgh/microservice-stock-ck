# 归档文档说明

本目录包含已过时或暂未实现的架构文档，保留用于历史参考。

## 归档时间

2026-01-08

## 目录结构

```
archive/
├── architecture-v1.md           # 初始架构设计 (50KB 巨型文件)
├── architecture-validation-v1.md # 初始架构验证报告
├── frontend/                     # 前端相关 (尚未实现)
│   ├── frontend-architecture.md
│   ├── frontend-coding-standards.md
│   ├── frontend-tech-stack.md
│   └── ui-design-system.md
└── legacy/                       # 其他历史文件
    ├── api-specification.md      # 初始 API 设计
    ├── backend-architecture.md   # 初始后端设计
    ├── components.md             # 组件设计
    ├── core-workflows.md         # 工作流设计
    ├── data-models.md            # 数据模型
    └── ...
```

## 归档原因

1. **architecture-v1.md**: 50KB 巨型文件，内容分散在多个主题，已拆分到各子目录
2. **frontend/**: 前端 UI 尚未实现，保留设计文档备用
3. **legacy/**: 初始架构设计阶段文档，与当前实现已有差异

## 如何使用

如需查阅历史设计决策，可参考这些文档。但请以 `docs/architecture/` 主目录下的文档为准。
