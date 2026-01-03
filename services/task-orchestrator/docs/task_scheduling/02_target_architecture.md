# 目标架构设计

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     目标架构 (3 服务)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              task-orchestrator                             │ │
│  │             (任务编排 + 通知)                              │ │
│  │  • 交易日历感知调度                                        │ │
│  │  • 任务 DAG 编排                                          │ │
│  │  • 告警通知                                               │ │
│  └───────────────────────────────────────────────────────────┘ │
│                          │                                      │
│              ┌───────────┴───────────┐                         │
│              ▼                       ▼                         │
│  ┌─────────────────────┐   ┌─────────────────────┐            │
│  │     gsd-api         │   │     gsd-worker      │            │
│  │    (查询服务)        │   │    (后台作业)       │            │
│  │  • /quotes          │   │  • /sync/*          │            │
│  │  • /kline           │   │  • /quality/*       │            │
│  │  • /market          │   │  • /repair/*        │            │
│  │                     │   │  • /jobs/*          │            │
│  │  水平扩展 (2-N)     │   │  单实例             │            │
│  └─────────────────────┘   └─────────────────────┘            │
│              │                       │                         │
│              └───────────┬───────────┘                         │
│                          ▼                                      │
│                    ClickHouse                                   │
└─────────────────────────────────────────────────────────────────┘
```

## 服务职责

| 服务 | 来源 | 职责 | 扩展策略 |
|:-----|:-----|:-----|:---------|
| **gsd-api** | get-stockdata (MODE=api) | 数据查询 | 水平扩展 |
| **gsd-worker** | get-stockdata (MODE=worker) | 同步/质量/修复 | 单实例+锁 |
| **task-orchestrator** | task-scheduler 升级 | 调度+通知 | 单实例 |

## 拆分方式

### 同镜像不同模式

```python
# main.py
MODE = os.getenv("MODE", "all")

if MODE in ["api", "all"]:
    app.include_router(quotes_router)
    app.include_router(kline_router)
    
if MODE in ["worker", "all"]:
    app.include_router(sync_router)
    app.include_router(quality_router)
```

### Docker Compose

```yaml
services:
  gsd-api:
    image: get-stockdata:latest
    environment:
      - MODE=api
    deploy:
      replicas: 2
      
  gsd-worker:
    image: get-stockdata:latest
    environment:
      - MODE=worker
```

## 每日任务链

```
18:10  [wait-upstream]   等待云端数据就绪
       ↓
18:15  [sync-kline]      MySQL → ClickHouse
       ↓
18:30  [daily-check]     完整性校验
       ↓ 通过              ↓ 失败
18:35  [strategy]        [auto-repair] 自动修复
       ↓                       ↓
19:00  [daily-report]    重新校验
```
