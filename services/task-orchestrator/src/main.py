import logging
import os
import json
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
from core.flow_controller import FlowController
from gsd_agent.core import SmartDecisionEngine

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Scheduler and Clients
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
docker_client = None
mysql_pool = None
task_logger = None
task_config: TaskConfig = None
flow_controller = None

async def auto_migrate():
    """启动时自动执行数据库迁移"""
    logger.info("🔧 Checking database schema...")
    
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 1. Ensure migrations_history table exists
                await cursor.execute("""
                    CREATE TABLE IF NOT EXISTS `alwaysup`.`migrations_history` (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        migration_name VARCHAR(255) UNIQUE NOT NULL,
                        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 2. Get list of all SQL files in migrations folder
                migrations_dir = Path(__file__).parent.parent / "migrations"
                sql_files = sorted(list(migrations_dir.glob("*.sql")))
                
                for migration_file in sql_files:
                    migration_name = migration_file.name
                    
                    # Check if already applied
                    await cursor.execute(
                        "SELECT id FROM alwaysup.migrations_history WHERE migration_name = %s",
                        (migration_name,)
                    )
                    if await cursor.fetchone():
                        continue
                        
                    logger.info(f"📝 Applying migration: {migration_name}...")
                    with open(migration_file, 'r', encoding='utf-8') as f:
                        sql_content = f.read()
                    
                    # Split and execute
                    statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
                    for stmt in statements:
                        await cursor.execute(stmt)
                    
                    # Mark as applied
                    await cursor.execute(
                        "INSERT INTO alwaysup.migrations_history (migration_name) VALUES (%s)",
                        (migration_name,)
                    )
                    await conn.commit()
                    logger.info(f"✓ Migration {migration_name} applied")
                
                logger.info("✓ Database schema is up to date")
    
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
    async def run_command_emitter_task(task: TaskDefinition):
        """Generic runner for Command Emitter tasks"""
        if not mysql_pool:
            logger.error("❌ MySQL pool not connected")
            return

        template_id = task.target.get('task_template')
        params_base = task.target.get('params', {})
        shards = task.target.get('shards', [None])
        
        # Calculate target date (Apply 6AM rule)
        from pytz import timezone
        cst = timezone('Asia/Shanghai')
        now = datetime.now(cst)
        if now.hour < 6:
            from datetime import timedelta
            target_date = (now - timedelta(days=1)).strftime("%Y%m%d")
        else:
            target_date = now.strftime("%Y%m%d")
            
        logger.info(f"📤 Emitting commands for task: {task.name} (Template: {template_id}, Shards: {shards})")
        
        try:
            async with mysql_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    for shard_id in shards:
                        params = params_base.copy()
                        params['date'] = target_date
                        if shard_id is not None:
                            params['shard_index'] = shard_id
                            
                        await cursor.execute(
                            "INSERT INTO alwaysup.task_commands (task_id, params, status) VALUES (%s, %s, %s)",
                            (template_id, json.dumps(params), "PENDING")
                        )
                    await conn.commit()
            logger.info(f"✅ Successfully emitted {len(shards)} commands to cloud.")
        except Exception as e:
            logger.error(f"❌ Failed to emit commands: {e}")
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
            "PYTHONPATH": "/app/src:/app/libs/gsd-shared:/app/libs/gsd-agent"
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
        
        # Ensure gsd-agent is mounted if it exists on host
        agent_path = os.path.join(settings.BASE_DIR, "libs/gsd-agent")
        if os.path.exists(agent_path):
            volumes_config[agent_path] = {'bind': '/app/libs/gsd-agent', 'mode': 'ro'}

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
            environment={"PYTHONPATH": "/app/src:/app/libs/gsd-shared"}
        )
        logger.info(f"🚀 Started Weekly Audit job (CID: {container_id})")
    except Exception as e:
        logger.error(f"❌ Failed to start Weekly Audit job: {e}")
        import traceback
        logger.error(traceback.format_exc())

async def run_stale_task_sweeper() -> None:
    """扫除长时间停留在 RUNNING 状态的僵尸任务 (防死锁)"""
    if not mysql_pool:
        return
        
    logger.info("🧹 Running Stale Task Sweeper...")
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 标记超过 2 小时未完成的任务为 FAILED
                await cursor.execute("""
                    UPDATE alwaysup.task_commands
                    SET 
                        status = 'FAILED',
                        result = CONCAT('Auto-recovered: Task stalled for over ', TIMESTAMPDIFF(MINUTE, executed_at, NOW()), ' minutes')
                    WHERE 
                        status = 'RUNNING' 
                        AND executed_at < NOW() - INTERVAL 2 HOUR
                """)
                affected = cursor.rowcount
                if affected > 0:
                    logger.warning(f"⚠️ Sweeper recovered {affected} stale tasks")
                await conn.commit()
    except Exception as e:
        logger.error(f"❌ Sweeper failed: {e}")

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
            # 0. Allow tasks without schedules to be registered for ad-hoc triggering
            trigger = None
            if task_def.schedule:
                # 1. 创建触发器
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
                
                elif task_def.type == TaskType.COMMAND_EMITTER:
                    async def emitter_wrapper(t=task_def):
                        await GenericTaskRunner.run_command_emitter_task(t)
                    job_func = emitter_wrapper
                    logger.info(f"  • {task_def.id}: Using Generic Command Emitter")

                elif task_def.type == TaskType.WORKFLOW_TRIGGER:
                    async def trigger_wrapper(t=task_def, params=None):
                        if not flow_controller:
                            logger.error("❌ FlowController not initialized")
                            return
                        
                        workflow_id = t.target.get('workflow_id')
                        logger.info(f"⚡ Triggering Workflow: {workflow_id} (Task: {t.name}, Dynamic Params: {params})")
                        
                        # Context preparation
                        from datetime import datetime
                        # 重要：合并 params 到 context
                        ctx = t.target.get('initial_context', {}).copy()
                        if params:
                            ctx.update(params)
                        
                        ctx['trigger_time'] = datetime.now().isoformat()
                        
                        # If date placeholder exists
                        if 'target_date' in ctx and ctx['target_date'] == '{{today_nodash}}':
                             ctx['target_date'] = datetime.now().strftime("%Y%m%d")

                        # We need to fetch definition first? 
                        # flow_controller.create_run takes definition object, not just ID.
                        # We need to extend FlowController to support Create Run by ID (it does lookup internally? No)
                        
                        # Let's check FlowController.create_run signature: 
                        # async def create_run(self, workflow_id: str, definition: WorkflowDefinition, ...)
                        
                        # We need to helper to fetch definition from DB first.
                        # Let's assume we implement a helper in GenericTaskRunner or just inline here.
                        
                        try:
                            async with mysql_pool.acquire() as conn:
                                async with conn.cursor(aiomysql.DictCursor) as cursor:
                                    await cursor.execute(
                                        "SELECT definition FROM alwaysup.workflow_definitions WHERE id = %s",
                                        (workflow_id,)
                                    )
                                    row = await cursor.fetchone()
                                    if not row:
                                        logger.error(f"❌ Workflow definition {workflow_id} not found in DB")
                                        return
                                    
                                    import json
                                    from core.workflow_parser import WorkflowDefinition
                                    def_json = row['definition']
                                    if isinstance(def_json, str):
                                        def_json = json.loads(def_json)
                                        
                                    wf_def = WorkflowDefinition.model_validate(def_json)
                                    
                                    run_id = await flow_controller.create_run(workflow_id, wf_def, ctx)
                                    logger.info(f"✅ Triggered Workflow Run: {run_id}")

                        except Exception as e:
                            logger.error(f"❌ Failed to trigger workflow: {e}")

                    job_func = trigger_wrapper
                    logger.info(f"  • {task_def.id}: Using Workflow Trigger")
                
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
                sched_desc = task_def.schedule.expression if task_def.schedule else "Ad-hoc/Manual"
                logger.info(f"  ✓ Registered: {task_def.name} ({sched_desc})")
        
        logger.info(f"✓ Registered all jobs from YAML")
    except Exception as e:
        logger.error(f"❌ Failed to register jobs: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global docker_client, mysql_pool, task_logger, task_config, flow_controller
    logger.info("🚀 Starting Task Orchestrator...")
    
    # Initialize command_poller to None for proper cleanup
    command_poller = None
    # flow_controller is global
    
    
    # 0. Initialize LLM Agent Engine
    api_keys = {
        "deepseek": settings.DEEPSEEK_API_KEY,
        "siliconflow": settings.SILICONFLOW_API_KEY,
        "openai": settings.OPENAI_API_KEY
    }
    # Filter out None values
    api_keys = {k: v for k, v in api_keys.items() if v}
    
    agent_engine = SmartDecisionEngine(
        api_keys=api_keys,
        redis_url=f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
        default_provider=settings.LLM_DEFAULT_PROVIDER
    )
    logger.info("✓ SmartDecisionEngine (gsd-agent) initialized")

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
    
    # 5.1 Register Internal Maintenance Jobs
    # 每 10 分钟运行一次僵尸任务清洗
    scheduler.add_job(
        run_stale_task_sweeper,
        CronTrigger(minute="*/10"),
        id="internal_task_sweeper",
        name="Stale Task Sweeper",
        replace_existing=True
    )
    logger.info("✓ Internal maintenance jobs registered")
    
    # 7. Start FlowController (Workflow 4.0 Engine)
    try:
        flow_controller = FlowController(mysql_pool, docker_client, agent_engine)
        await flow_controller.start()
        logger.info("✓ FlowController started")
    except Exception as e:
        logger.error(f"❌ Failed to start FlowController: {e}")

    # 6. Start Command Poller (Cloud -> Local)
    # 只有当配置了云端 MySQL 时才启动，或者默认启动因为 alwaysup 库在云端
    try:
        from core.command_poller import CommandPoller
        command_poller = CommandPoller(mysql_pool, scheduler, docker_client, task_config, flow_controller=flow_controller)
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

    if flow_controller:
        # Assuming FlowController also has a stop method mirroring CommandPoller
        flow_controller._running = False
        if flow_controller._task:
            flow_controller._task.cancel()
            
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
