# 盘前数据准备与校验方案 (Gate-1)

## 1. 目标

在每个交易日开盘前 (08:00-09:20)，自动完成：
1. **昨日数据完整性校验** - K线、分笔覆盖率检查
2. **自动补采触发** - 数据不足时触发补采任务
3. **告警通知** - 通过企业微信发送状态报告
4. **支持手动触发** - 小程序通过 MySQL 队列触发任务

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              公网 (腾讯云)                                   │
│  ┌─────────────┐     ┌───────────────────┐     ┌────────────────────────┐   │
│  │  微信小程序  │────▶│  cloud-api:8000   │────▶│ 云端 MySQL (alwaysup) │   │
│  │  (用户手机)  │     │  (备案域名访问)    │     │   task_commands 表    │   │
│  └─────────────┘     └───────────────────┘     └───────────┬────────────┘   │
└────────────────────────────────────────────────────────────│────────────────┘
                                                             │ GOST 隧道
                                                             │ (已建立)
┌────────────────────────────────────────────────────────────│────────────────┐
│                              内网 (Server 41)              ▼                 │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        task-orchestrator:18000                         │  │
│  │  ┌─────────────────────┐    ┌─────────────────────────────────────┐   │  │
│  │  │   CommandPoller     │───▶│         APScheduler                 │   │  │
│  │  │ (轮询 task_commands) │    │ (执行 pre_market_gate, sync_kline) │   │  │
│  │  └─────────────────────┘    └─────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                       │
│                      ┌───────────────┼───────────────┐                       │
│                      ▼               ▼               ▼                       │
│              ┌────────────┐  ┌────────────┐  ┌────────────┐                  │
│              │ ClickHouse │  │   Redis    │  │ gsd-worker │                  │
│              │ (数据校验)  │  │ (股票列表) │  │ (补采执行) │                  │
│              └────────────┘  └────────────┘  └────────────┘                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 云端实现 (腾讯云)

### 3.1 新建数据表 (`alwaysup.task_commands`)

```sql
CREATE TABLE IF NOT EXISTS `task_commands` (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL COMMENT '任务ID，如 pre_market_gate',
    params JSON COMMENT '可选参数，如 {"target_date": "20260113"}',
    status ENUM('PENDING', 'RUNNING', 'DONE', 'FAILED') DEFAULT 'PENDING',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    executed_at DATETIME,
    result TEXT COMMENT '执行结果或错误信息',
    INDEX idx_status (status)
) COMMENT='异步任务命令队列';
```

### 3.2 云端 API 端点 (`cloud-api`)

**文件**: `cloud-api/routes/task_commands.py`

```python
from fastapi import APIRouter
import pymysql.cursors

router = APIRouter()

@router.post("/api/v1/commands")
async def create_command(task_id: str, params: dict = None):
    """
    小程序调用此接口，将触发命令写入 MySQL 队列
    """
    conn = get_cloud_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO task_commands (task_id, params) VALUES (%s, %s)",
            (task_id, json.dumps(params) if params else None)
        )
    conn.commit()
    return {"status": "queued", "task_id": task_id}

@router.get("/api/v1/commands/{command_id}")
async def get_command_status(command_id: int):
    """查询命令执行状态"""
    # ... 实现略
```

---

## 4. 内网实现 (Server 41)

### 4.1 数据校验逻辑 (`gsd-worker/src/jobs/pre_market_gate.py`)

```python
import asyncio
from clickhouse_driver import Client
from datetime import datetime, timedelta

KLINE_THRESHOLD = 98  # K线覆盖率阈值 (%)
TICK_THRESHOLD = 95   # 分笔覆盖率阈值 (%)

async def run():
    """盘前数据质量校验主函数"""
    yesterday = get_yesterday_trading_date()
    
    # 1. 查询覆盖率
    kline_rate = await check_kline_coverage(yesterday)
    tick_rate = await check_tick_coverage(yesterday)
    
    # 2. 判断是否需要补采
    recovery_needed = False
    if kline_rate < KLINE_THRESHOLD:
        await trigger_task("daily_kline_sync", target_date=yesterday)
        recovery_needed = True
        
    if tick_rate < TICK_THRESHOLD:
        await trigger_task("sync_tick", target_date=yesterday)
        recovery_needed = True
    
    # 3. 发送告警/状态报告
    await send_pre_market_report(kline_rate, tick_rate, recovery_needed)

async def check_kline_coverage(date: str) -> float:
    """检查K线覆盖率"""
    client = Client(host='127.0.0.1')
    result = client.execute(f"""
        SELECT countDistinct(stock_code) / 5300 * 100 
        FROM stock_data.stock_kline_daily 
        WHERE trade_date = '{date}'
    """)
    return result[0][0]

async def check_tick_coverage(date: str) -> float:
    """检查分笔覆盖率"""
    client = Client(host='127.0.0.1')
    result = client.execute(f"""
        SELECT countDistinct(stock_code) / 5300 * 100 
        FROM stock_data.tick_data 
        WHERE trade_date = '{date}'
    """)
    return result[0][0]
```

### 4.2 命令轮询器 (`task-orchestrator/src/core/command_poller.py`)

```python
import asyncio
import aiomysql
import logging

logger = logging.getLogger(__name__)

class CommandPoller:
    """轮询云端 MySQL 的 task_commands 表，执行待处理命令"""
    
    def __init__(self, mysql_pool, scheduler, poll_interval: int = 15):
        self.mysql_pool = mysql_pool
        self.scheduler = scheduler
        self.poll_interval = poll_interval
        self._running = False
    
    async def start(self):
        """启动轮询"""
        self._running = True
        logger.info(f"🔄 CommandPoller 启动，轮询间隔 {self.poll_interval}s")
        while self._running:
            await self._poll_and_execute()
            await asyncio.sleep(self.poll_interval)
    
    async def stop(self):
        """停止轮询"""
        self._running = False
        logger.info("🛑 CommandPoller 已停止")
    
    async def _poll_and_execute(self):
        """单次轮询并执行"""
        async with self.mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 1. 获取一条 PENDING 命令
                await cursor.execute("""
                    SELECT id, task_id, params 
                    FROM alwaysup.task_commands 
                    WHERE status = 'PENDING' 
                    ORDER BY created_at 
                    LIMIT 1 FOR UPDATE
                """)
                cmd = await cursor.fetchone()
                if not cmd:
                    return
                
                cmd_id = cmd['id']
                task_id = cmd['task_id']
                
                # 2. 更新状态为 RUNNING
                await cursor.execute(
                    "UPDATE alwaysup.task_commands SET status='RUNNING', executed_at=NOW() WHERE id=%s",
                    (cmd_id,)
                )
                await conn.commit()
                
                # 3. 执行任务
                try:
                    self.scheduler.modify_job(task_id, next_run_time=datetime.now())
                    result = "SUCCESS"
                    status = "DONE"
                    logger.info(f"✅ 执行命令 #{cmd_id}: {task_id}")
                except Exception as e:
                    result = str(e)
                    status = "FAILED"
                    logger.error(f"❌ 命令 #{cmd_id} 执行失败: {e}")
                
                # 4. 更新结果
                await cursor.execute(
                    "UPDATE alwaysup.task_commands SET status=%s, result=%s WHERE id=%s",
                    (status, result, cmd_id)
                )
                await conn.commit()
```

### 4.3 任务配置 (`config/tasks.yml`)

```yaml
- id: pre_market_gate
  name: 盘前数据质量门禁
  type: docker
  enabled: true
  schedule:
    type: trading_cron
    expression: "0 8 * * 1-5"  # 08:00 交易日
  target:
    command: ["jobs.pre_market_gate"]
    environment:
      KLINE_THRESHOLD: "98"
      TICK_THRESHOLD: "95"
  retry:
    max_attempts: 1
```

---

## 5. 实施步骤

### 云端任务
| 阶段 | 任务 | 预估时间 |
|:-----|:-----|:---------|
| C1 | 创建 `task_commands` 表 | 0.5h |
| C2 | 新增 `cloud-api` 的 `/commands` 端点 | 1h |

### 内网任务
| 阶段 | 任务 | 预估时间 |
|:-----|:-----|:---------|
| L1 | 新增 `pre_market_gate.py` Job 脚本 | 2h |
| L2 | 新增 `CommandPoller` 轮询器 | 2h |
| L3 | 扩展 `tasks.yml` 配置 | 0.5h |
| L4 | 集成测试与告警验证 | 2h |

**总计**: ~8 小时

---

## 6. 待确认事项

1. 轮询间隔设为 15 秒是否满足需求？
2. 补采失败是否需要重试？（建议：是，最多 2 次）
3. 企业微信告警 Webhook 地址？
