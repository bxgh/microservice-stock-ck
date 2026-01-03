# 实施路线图

## 总体规划

```
Phase 1          Phase 2           Phase 3          Phase 4
Week 1           Week 2            Week 3           Week 4
───────────────────────────────────────────────────────────
服务拆分         调度升级           集成测试          上线
├─ MODE 切换    ├─ 日历触发器      ├─ 模拟交易日     ├─ 灰度发布
├─ API 端点     ├─ 任务 DAG        ├─ 模拟非交易日   └─ 全量切换
└─ Docker 配置  └─ 告警接入        └─ 故障演练
```

## Phase 1: 服务拆分 (Week 1)

### 任务清单

- [ ] 修改 `main.py` 添加 MODE 判断
- [ ] 更新 `docker-compose.yml` 双服务配置
- [ ] 新增 `/jobs/*` 标准任务端点
- [ ] 测试 api/worker 模式分别启动

### 交付物

| 文件 | 改动 |
|:-----|:-----|
| main.py | +20 行 MODE 判断 |
| docker-compose.yml | +1 个 gsd-worker 服务 |
| jobs_routes.py | 新文件 |

---

## Phase 2: 调度升级 (Week 2)

### 任务清单

- [ ] 实现 TradingCalendarTrigger
- [ ] 实现简单任务链 (顺序依赖)
- [ ] 接入企微 Webhook
- [ ] 新增 `/quality/daily-check` API

### 交付物

| 文件 | 说明 |
|:-----|:-----|
| trading_calendar.py | 交易日历触发器 |
| workflow_engine.py | 任务链引擎 |
| notify_service.py | 通知服务 |

---

## Phase 3: 集成测试 (Week 3)

### 测试场景

| 场景 | 验证点 |
|:-----|:-------|
| 交易日正常流程 | 同步→校验→策略→报告 |
| 非交易日跳过 | 任务不触发 |
| 数据缺失 < 50 | 自动修复成功 |
| 数据缺失 ≥ 50 | 告警发送 |
| 同步失败 | 重试后成功/告警 |

---

## Phase 4: 上线 (Week 4)

### 灰度策略

1. 先部署 gsd-worker，仍用旧调度
2. 切换到 task-orchestrator 调度
3. 观察 3 天无异常后全量
4. 保留旧方式回滚能力

---

## 新增 API 清单

| API | 方法 | 服务 | 说明 |
|:----|:-----|:-----|:-----|
| `/sync/wait-upstream` | GET | gsd-worker | 等待云端就绪 |
| `/quality/daily-check` | GET | gsd-worker | 综合校验 |
| `/repair/auto` | POST | gsd-worker | 自动修复 |
| `/jobs/kline-sync` | POST | gsd-worker | 任务入口 |
| `/notify/send` | POST | orchestrator | 发送通知 |
