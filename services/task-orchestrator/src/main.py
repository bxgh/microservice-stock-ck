import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import docker
import aiomysql
from datetime import datetime
from pathlib import Path

from config.settings import settings
from config.task_loader import TaskLoader, TaskConfig, ScheduleType
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
            # 创建触发器
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
            
            # 注册任务
            # TODO: 根据任务类型创建不同的执行函数
            # 暂时使用硬编码的 job_daily_sync_kline
            if task_def.id == "daily_kline_sync":
                scheduler.add_job(
                    job_daily_sync_kline,
                    trigger,
                    id=task_def.id,
                    name=task_def.name,
                    replace_existing=True
                )
                logger.info(f"📅 Registered: {task_def.name} ({task_def.schedule.expression})")
        
        logger.info(f"✓ Registered {len(enabled_tasks)} jobs")
    except Exception as e:
        logger.error(f"❌ Failed to register jobs: {e}")
        raise

async def job_daily_sync_kline() -> None:
    """Daily K-Line Sync & Quality Check Workflow"""
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
    # Enable deep scan to fill the ledger for repair
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
    
    await engine.run_workflow(workflow)

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

@app.post("/debug/trigger/{job_name}")
async def trigger_job(job_name: str) -> dict:
    """
    Manually trigger a job (Debug only)
    Example: /debug/trigger/sync_kline
    """
    from executor.docker_executor import DockerExecutor
    
    if not docker_client:
        return {"error": "Docker not connected"}
        
    executor = DockerExecutor(docker_client)
    
    try:
        if job_name == "sync_kline":
            # Run a dummy sync (shard 0/1)
            # Dockerfile has ENTRYPOINT ["python", "-m"]
            cmd = ["jobs.sync_kline", "--shard", "0", "--total", "1"]
            cid = executor.run_worker(
                command=cmd,
                name_suffix=f"manual-{job_name}",
                environment={"ENVIRONMENT": "development"}
            )
            return {"status": "started", "container_id": cid, "job": job_name}
            
        return {"error": "Unknown job"}
        
    except Exception as e:
        return {"error": str(e)}

@app.post("/debug/workflow/{name}")
async def trigger_workflow(name: str) -> dict:
    """
    Trigger a complex workflow
    """
    from executor.docker_executor import DockerExecutor
    from core.dag_engine import DAGEngine, Workflow, Task
    from gsd_shared.utils.calendar_service import CalendarService
    
    # 1. Check Calendar (Demo)
    cal = CalendarService()
    is_trading = cal.is_trading_day()
    logger.info(f"📅 Today is trading day? {is_trading}")
    
    if not docker_client:
        return {"error": "Docker not connected"}
        
    executor = DockerExecutor(docker_client)
    engine = DAGEngine(executor)
    
    if name == "sync_kline_full":
        # Create a DAG:
        # Task 1: Sync Shard 0
        # Task 2: Sync Shard 1
        # Task 3: Verify (Depends on 1 & 2)
        
        task1 = Task(
            id="sync-shard-0",
            name="Sync K-Line Shard 0",
            command=["jobs.sync_kline", "--shard", "0", "--total", "2"]
        )
        
        task2 = Task(
            id="sync-shard-1",
            name="Sync K-Line Shard 1",
            command=["jobs.sync_kline", "--shard", "1", "--total", "2"]
        )
        
        task3 = Task(
            id="finalize",
            name="Finalize Sync",
            command=["jobs.sync_kline", "--help"], # Dummy command for now
            dependencies={"sync-shard-0", "sync-shard-1"}
        )
        
        workflow = Workflow(
            name="Manual K-Line Sync Workflow",
            tasks=[task1, task2, task3]
        )
        
        # Fire and forget (in background)
        # In real app, we track run ID
        import asyncio
        asyncio.create_task(engine.run_workflow(workflow))
        
        return {"status": "started", "workflow": name, "trading_day": is_trading}
        
    return {"error": "Unknown workflow"}

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
    uvicorn.run("main:app", host="0.0.0.0", port=18000, reload=settings.DEBUG)
