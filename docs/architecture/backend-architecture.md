# Backend Architecture

## Service Organization
```
microservice-stock/services/task-scheduler/src/
├── routes/              # API 路由控制器
├── services/            # 业务逻辑层
├── models/              # 数据模型层
├── database/            # 数据库相关
├── middleware/          # 中间件
├── utils/               # 工具函数
├── scheduler/           # 调度器核心
├── main.py              # 应用入口
└── config.py            # 配置管理
```

## Controller Template
```python
# routes/tasks.py
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/")
async def get_tasks(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None
):
    """获取任务列表"""
    # 实现逻辑
    pass

@router.post("/", status_code=201)
async def create_task(task_data: CreateTaskRequest):
    """创建新任务"""
    # 实现逻辑
    pass
```
