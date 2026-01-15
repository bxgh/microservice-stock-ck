import logging
import os
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
from core.dag_engine import DAGEngine, Workflow, Task as DagTask
from executor.docker_executor import DockerExecutor

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
        # Prepare Environment: Merge task-specific env with default worker settings
        env = {}
        # 1. Start with defaults from orchestrator settings
        env.update({
            "MYSQL_HOST": settings.WORKER_MYSQL_HOST,
            "MYSQL_PORT": str(settings.WORKER_MYSQL_PORT),
            "MYSQL_USER": settings.WORKER_MYSQL_USER,
            "MYSQL_PASSWORD": settings.WORKER_MYSQL_PASSWORD,
            "MYSQL_DATABASE": settings.WORKER_MYSQL_DATABASE,
            "CLICKHOUSE_HOST": settings.WORKER_CLICKHOUSE_HOST,
            "CLICKHOUSE_PORT": str(settings.WORKER_CLICKHOUSE_PORT),
            "CLICKHOUSE_USER": settings.WORKER_CLICKHOUSE_USER,
            "CLICKHOUSE_PASSWORD": settings.WORKER_CLICKHOUSE_PASSWORD,
            "CLICKHOUSE_DATABASE": settings.WORKER_CLICKHOUSE_DATABASE,
            "MOOTDX_API_URL": settings.WORKER_MOOTDX_API_URL,
            "TZ": settings.TIMEZONE,
            "PYTHONPATH": "/app/src"
        })
        # 2. Override with task-specific environment variables
        task_env = task.target.get('environment')
        if task_env:
            env.update(task_env)

        network_mode = task.target.get('network_mode', 'host')

        # 3. Prepare Volumes
        # 汇总全局默认挂载 + 任务特定挂载
        volumes_config = {}
        
        # A. 从 global.docker.default_volumes 获取 (如果有)
        if task_config and task_config.global_ and task_config.global_.docker:
            default_vols = task_config.global_.docker.get('default_volumes', [])
            for v in default_vols:
                parts = v.split(':')
                if len(parts) >= 2:
                    host_path = parts[0]
                    if host_path.startswith('.'):
                        host_path = os.path.join(settings.BASE_DIR, host_path.lstrip('./'))
                    volumes_config[host_path] = {'bind': parts[1], 'mode': parts[2] if len(parts) > 2 else 'rw'}

        # B. 从任务 target.volumes 获取
        task_vols = task.target.get('volumes', [])
        for v in task_vols:
            parts = v.split(':')
            if len(parts) >= 2:
                host_path = parts[0]
                if host_path.startswith('.'):
                    host_path = os.path.join(settings.BASE_DIR, host_path.lstrip('./'))
                volumes_config[host_path] = {'bind': parts[1], 'mode': parts[2] if len(parts) > 2 else 'rw'}

        logger.info(f"▶️ Executing Docker task: {task.name} ({image}) net={network_mode} vols={len(volumes_config)}")
        try:
            container = docker_client.containers.run(
                image=image,
                command=command,
                environment=env,
                volumes=volumes_config,
                detach=True,
                network_mode=network_mode,
                remove=False  # Keep container for debugging
            )
            logger.info(f"✅ Docker Task started: {task.name} - CID {container.id[:12]}")
        except Exception as e:
            logger.error(f"❌ Docker Task failed: {task.name} - {e}")
            raise

    @staticmethod
    async def run_workflow_task(task: TaskDefinition):
        """Generic runner for Workflow tasks"""
        if not docker_client:
            logger.error("❌ Docker client not connected")
            return

        executor = DockerExecutor(docker_client)
        engine = DAGEngine(executor)
        
        # Convert TaskDefinition workflow steps to DAG Engine Tasks
        dag_tasks = []
        for step in task.workflow:
            # If step has 'tasks' list (parallel group), we need to flatten/expand it? 
            # DAGEngine supports simple list of tasks with deps.
            # The TaskLoader defines: workflow: Optional[List[WorkflowStep]]
            # WorkflowStep: id, command, parallel, tasks(list of dicts)
            
            if step.parallel and step.tasks:
                # Expand parallel tasks
                for sub_task in step.tasks:
                    sub_id = sub_task.get('id')
                    sub_cmd = sub_task.get('command')
                    
                    # Merge environment
                    env = {}
                    # Inherit workflow global env if any (not on task def currently, but maybe in future)
                    
                    dt = DagTask(
                        id=f"{task.id}-{step.id}-{sub_id}", # Unique global ID
                        name=f"{task.name}-{sub_id}",
                        command=sub_cmd,
                        dependencies=set([f"{task.id}-{d}" for d in step.depends_on]) if step.depends_on else set()
                    )
                    dag_tasks.append(dt)
            else:
                # Single step task
                dt = DagTask(
                    id=f"{task.id}-{step.id}",
                    name=f"{task.name}-{step.id}",
                    command=step.command,
                    dependencies=set([f"{task.id}-{d}" for d in step.depends_on]) if step.depends_on else set()
                )
                dag_tasks.append(dt)


        workflow = Workflow(name=task.name, tasks=dag_tasks)
        success = await engine.run_workflow(workflow)
        
        if not success:
            raise Exception(f"Workflow {task.name} failed")

# --- Custom Job Handlers ---

# Removed deprecated job_daily_kline_sync function
# K-line sync now uses single-process mode via generic Docker runner
# Configuration is in tasks.yml: command: ["jobs.sync_kline"]


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
        
        # 注册所有任务
        for task_def in task_config.tasks:
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
            special_handler_name = f"job_{task_def.id}"
            if special_handler_name in globals():
                job_func = globals()[special_handler_name]
                logger.info(f"  • {task_def.id}: Using specialized handler '{special_handler_name}'")
            
            # B. 如果没有特殊 Handler，使用通用 Runner
            else:
                if task_def.type == TaskType.HTTP:
                    async def http_wrapper(t=task_def):
                        await GenericTaskRunner.run_http_task(t)
                    job_func = http_wrapper
                    logger.info(f"  • {task_def.id}: Using Generic HTTP Runner")
                    
                elif task_def.type == TaskType.DOCKER:
                    async def docker_wrapper(t=task_def):
                        await GenericTaskRunner.run_docker_task(t)
                    job_func = docker_wrapper
                    logger.info(f"  • {task_def.id}: Using Generic Docker Runner")

                elif task_def.type == TaskType.WORKFLOW:
                    async def workflow_wrapper(t=task_def):
                        await GenericTaskRunner.run_workflow_task(t)
                    job_func = workflow_wrapper
                    logger.info(f"  • {task_def.id}: Using Generic Workflow Runner")
                
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
            
            # 4. 如果任务被禁用，则暂停它
            if not task_def.enabled:
                scheduler.pause_job(task_def.id)
                logger.info(f"  ✓ Registered (Paused): {task_def.name}")
            else:
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
    
    # Initialize command_poller to None for proper cleanup
    command_poller = None
    
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
    
    # 6. Start Command Poller (Cloud -> Local)
    # 只有当配置了云端 MySQL 时才启动，或者默认启动因为 alwaysup 库在云端
    try:
        from core.command_poller import CommandPoller
        command_poller = CommandPoller(mysql_pool, scheduler, docker_client, task_config)
        await command_poller.start()
        logger.info("✓ CommandPoller started")
    except Exception as e:
        logger.error(f"⚠️ Failed to start CommandPoller: {e}")
        logger.warning("Orchestrator will continue without remote command polling")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Task Orchestrator...")
    
    if command_poller:
        try:
            await command_poller.stop()
        except Exception as e:
            logger.error(f"Error stopping CommandPoller: {e}")
        
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
