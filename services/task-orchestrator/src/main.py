import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import docker

from config.settings import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Scheduler
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
docker_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global docker_client
    logger.info("🚀 Starting Task Orchestrator...")
    
    # Initialize Docker Client
    try:
        docker_client = docker.DockerClient(base_url=settings.DOCKER_HOST)
        version = docker_client.version()
        logger.info(f"🐳 Connected to Docker Engine v{version.get('Version')}")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Docker: {e}")
        # We might want to exit here if Docker is critical, but for now just log
    
    # Start Scheduler
    scheduler.start()
    logger.info("⏰ Scheduler started")
    
    # Add default jobs (Example)
    # scheduler.add_job(check_upstream, 'interval', minutes=5)
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Task Orchestrator...")
    scheduler.shutdown()
    if docker_client:
        docker_client.close()

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan
)

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
async def trigger_job(job_name: str):
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

@app.get("/jobs")
async def list_jobs():
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
