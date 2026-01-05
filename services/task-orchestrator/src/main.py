import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import docker
import aiomysql
import httpx
from datetime import datetime
from pathlib import Path

from config.settings import settings
from config.task_loader import TaskLoader, TaskConfig, ScheduleType, TaskDefinition, TaskType
from core.logger_service import TaskLogger

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Scheduler and Clients
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
docker_client = None
mysql_pool = None
task_logger = None
task_config: TaskConfig = None

async def auto_migrate():
    """启动时自动执行数据库迁移"""
    logger.info("🔧 Checking database schema...")
    
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 检查表是否存在
                await cursor.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_name = 'task_execution_logs'",
                    (settings.MYSQL_DATABASE,)
                )
                result = await cursor.fetchone()
                
                if result[0] == 0:
                    logger.info("📝 Creating task_execution_logs table...")
                    
                    # 读取迁移SQL文件
                    migration_file = Path(__file__).parent.parent / "migrations" / "001_task_logs.sql"
                    with open(migration_file, 'r', encoding='utf-8') as f:
                        sql_content = f.read()
                    
                    # 分割并执行SQL语句
                    statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
                    
                    for stmt in statements:
                        if stmt:
                            await cursor.execute(stmt)
                    
                    await conn.commit()
                    logger.info("✓ Database migration completed")
                else:
                    logger.info("✓ Database schema up to date")
    
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

# --- Generic Runners ---

class GenericTaskRunner:
    @staticmethod
    async def run_http_task(task: TaskDefinition):
        """Generic runner for HTTP tasks"""
        method = task.target.get('method', 'POST')
        url = task.target.get('url')
        timeout = task.target.get('timeout_seconds', 30)
        
        logger.info(f"▶️ Executing HTTP task: {task.name} ({method} {url})")
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=task.target.get('headers'),
                    content=task.target.get('body')
                )
                response.raise_for_status()
                logger.info(f"✅ HTTP Task success: {task.name} - Status {response.status_code}")
                # Log execution success (TODO: Integrate with TaskLogger)
            except Exception as e:
                logger.error(f"❌ HTTP Task failed: {task.name} - {e}")
                raise

    @staticmethod
    async def run_docker_task(task: TaskDefinition):
        """Generic runner for Docker tasks"""
        if not docker_client:
            logger.error("❌ Docker client not connected")
            return

        image = task.target.get('image') or settings.WORKER_IMAGE
        command = task.target.get('command')
        environment = task.target.get('environment')

        logger.info(f"▶️ Executing Docker task: {task.name} ({image})")
        try:
            container = docker_client.containers.run(
                image=image,
                command=command,
                environment=environment,
                detach=True,
                remove=True  # Auto-remove after run? Or track status?
            )
            logger.info(f"✅ Docker Task started: {task.name} - CID {container.id[:12]}")
        except Exception as e:
            logger.error(f"❌ Docker Task failed: {task.name} - {e}")
            raise

# --- Custom Job Handlers ---

async def job_daily_kline_sync() -> None:
    """Daily K-Line Sync & Quality Check Workflow (Specialized Logic)"""
    from executor.docker_executor import DockerExecutor
    from core.dag_engine import DAGEngine, Workflow, Task
    
    if not docker_client:
        logger.error("❌ Docker client not connected, skipping job")
        return
        
    executor = DockerExecutor(docker_client)
    engine = DAGEngine(executor)
    
    # Define Workflow
    total_shards = 4 
    sync_tasks = []
    
    # Step 1: Sync Shards
    for i in range(total_shards):
        sync_tasks.append(Task(
            id=f"sync-shard-{i}",
            name=f"K-Line Sync Shard {i}",
            command=["jobs.sync_kline", "--shard", str(i), "--total", str(total_shards)],
            environment={"PYTHONPATH": "/app/src"}
        ))
    
    # Step 2: Quality Check (Depends on ALL shards)
    quality_task = Task(
        id="quality-check",
        name="Data Quality Daily Check",
        command=["jobs.quality_check", "--deep", "--batch", "100"],
        dependencies={t.id for t in sync_tasks},
        environment={"PYTHONPATH": "/app/src"}
    )
    
    # Step 3: Data Repair (Depends on Quality Check)
    repair_task = Task(
        id="data-repair",
        name="Auto Data Repair",
        command=["jobs.data_repair", "--limit", "20"],
        dependencies={quality_task.id},
        environment={"PYTHONPATH": "/app/src"}
    )
    
    workflow = Workflow(
        name="Daily Market Sync & Quality Check",
        tasks=sync_tasks + [quality_task, repair_task]
    )
    
    logger.info("🚀 Starting Daily Market Sync workflow...")
    await engine.run_workflow(workflow)

async def job_weekly_deep_audit() -> None:
    """Weekly Deep Audit Job (Specialized Logic)"""
    from executor.docker_executor import DockerExecutor
    
    logger.info("🛠️ Manual/Scheduled execution started: weekly_deep_audit")
    if not docker_client:
        logger.error("❌ Docker client not connected, skipping job")
        return
        
    executor = DockerExecutor(docker_client)
    
    # Run the worker with weekly_audit command
    try:
        container_id = executor.run_worker(
            command=["jobs.weekly_audit"],
            name_suffix="weekly-audit",
            environment={"PYTHONPATH": "/app/src"}
        )
        logger.info(f"🚀 Started Weekly Audit job (CID: {container_id})")
    except Exception as e:
        logger.error(f"❌ Failed to start Weekly Audit job: {e}")
        import traceback
        logger.error(traceback.format_exc())

# --- Registration Logic ---

async def register_jobs() -> None:
    """Register all scheduled jobs from YAML configuration"""
    global task_config
    
    logger.info(f"🔧 Registering {len(task_config.tasks)} jobs from YAML...")
    
    try:
        from scheduler.triggers import TradingDayTrigger
        from gsd_shared.utils.calendar_service import CalendarService
        
        cal_service = CalendarService()
        
        # 只注册启用的任务
        enabled_tasks = [t for t in task_config.tasks if t.enabled]
        
        for task_def in enabled_tasks:
            # 1. 创建触发器
            trigger = None
            if task_def.schedule.type == ScheduleType.TRADING_CRON:
                base_trigger = CronTrigger.from_crontab(
                    task_def.schedule.expression,
                    timezone=settings.TIMEZONE
                )
                trigger = TradingDayTrigger(base_trigger, cal_service)
            elif task_def.schedule.type == ScheduleType.CRON:
                trigger = CronTrigger.from_crontab(
                    task_def.schedule.expression,
                    timezone=settings.TIMEZONE
                )
            else:
                logger.warning(f"Skipping task {task_def.id}: unsupported schedule type {task_def.schedule.type}")
                continue
            
            # 2. 确定执行函数
            job_func = None
            
            # A. 优先查找是否存在特定的 Handler 函数 (job_{task_id})
            # 这样可以保留复杂的 DAG 逻辑或特殊处理
            special_handler_name = f"job_{task_def.id}"
            if special_handler_name in globals():
                job_func = globals()[special_handler_name]
                logger.info(f"  • {task_def.id}: Using specialized handler '{special_handler_name}'")
            
            # B. 如果没有特殊 Handler，使用通用 Runner
            else:
                if task_def.type == TaskType.HTTP:
                    # 使用闭包或 functools.partial 来绑定 task_def
                    # 这里定义一个 wrapper
                    async def http_wrapper(t=task_def):
                        await GenericTaskRunner.run_http_task(t)
                    job_func = http_wrapper
                    logger.info(f"  • {task_def.id}: Using Generic HTTP Runner")
                    
                elif task_def.type == TaskType.DOCKER:
                    async def docker_wrapper(t=task_def):
                        await GenericTaskRunner.run_docker_task(t)
                    job_func = docker_wrapper
                    logger.info(f"  • {task_def.id}: Using Generic Docker Runner")
                
                else:
                    logger.warning(f"Skipping task {task_def.id}: unsupported task type {task_def.type}")
                    continue

            # 3. 注册到 Scheduler
            scheduler.add_job(
                job_func,
                trigger,
                id=task_def.id,
                name=task_def.name,
                replace_existing=True
            )
            logger.info(f"  ✓ Registered: {task_def.name} ({task_def.schedule.expression})")
        
        logger.info(f"✓ Registered all jobs from YAML")
    except Exception as e:
        logger.error(f"❌ Failed to register jobs: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global docker_client, mysql_pool, task_logger, task_config
    logger.info("🚀 Starting Task Orchestrator...")
    
    # 1. Initialize MySQL Connection Pool
    try:
        mysql_pool = await aiomysql.create_pool(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            db=settings.MYSQL_DATABASE,
            minsize=1,
            maxsize=settings.MYSQL_POOL_SIZE
        )
        logger.info(f"✓ MySQL pool created ({settings.MYSQL_HOST}:{settings.MYSQL_PORT})")
        
        # 自动执行数据库迁移
        await auto_migrate()
        
        # Initialize Task Logger
        task_logger = TaskLogger(mysql_pool)
        logger.info("✓ TaskLogger initialized")
    except Exception as e:
        logger.error(f"❌ Failed to connect to MySQL: {e}")
        raise
    
    # 2. Initialize Docker Client
    try:
        docker_client = docker.DockerClient(base_url=settings.DOCKER_HOST)
        version = docker_client.version()
        logger.info(f"🐳 Connected to Docker Engine v{version.get('Version')}")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Docker: {e}")
        raise
    
    # 3. Load Task Configuration from YAML
    try:
        config_path = Path(__file__).parent.parent / "config" / "tasks.yml"
        loader = TaskLoader()
        task_config = loader.load_from_yaml(str(config_path))
        logger.info(f"✓ Loaded {len(task_config.tasks)} tasks from YAML")
    except Exception as e:
        logger.error(f"❌ Failed to load task configuration: {e}")
        raise
    
    # 4. Start Scheduler
    scheduler.start()
    logger.info("⏰ Scheduler started")
    
    # 5. Register Scheduled Jobs
    await register_jobs()
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Task Orchestrator...")
    scheduler.shutdown()
    
    if docker_client:
        docker_client.close()
    
    if mysql_pool:
        mysql_pool.close()
        await mysql_pool.wait_closed()
        logger.info("✓ MySQL pool closed")

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan
)

# Mount API routes
from api.tasks import router as tasks_router
app.include_router(tasks_router, prefix="/api/v1", tags=["tasks"])

# Prometheus metrics
from prometheus_client import make_asgi_app
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    docker_status = "ok"
    try:
        if docker_client:
            docker_client.ping()
        else:
            docker_status = "disconnected"
    except Exception:
        docker_status = "error"
        
    return {
        "status": "ok",
        "scheduler": "running" if scheduler.running else "stopped",
        "docker": docker_status
    }

@app.get("/jobs")
async def list_jobs() -> list:
    """List scheduled jobs"""
    jobs = scheduler.get_jobs()
    return [
        {
            "id": job.id,
            "next_run_time": job.next_run_time,
            "name": job.name
        } 
        for job in jobs
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=18000)
