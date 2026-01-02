import logging
import docker
from typing import Dict, List, Optional
from config.settings import settings

logger = logging.getLogger(__name__)

class DockerExecutor:
    """Docker Container Executor"""
    
    def __init__(self, client: docker.DockerClient):
        self.client = client
        
    def run_worker(self, 
                   command: List[str], 
                   environment: Optional[Dict[str, str]] = None,
                   name_suffix: str = "") -> str:
        """
        Run gsd-worker container
        
        Args:
            command: Command list (e.g. ["python", "-m", "jobs.sync_kline"])
            environment: Environment variables
            name_suffix: Container name suffix
            
        Returns:
            Container ID
        """
        try:
            image = settings.WORKER_IMAGE
            # Ensure image exists (pull if needed, or skip if local)
            # self.client.images.pull(image) # Optional/Slow
            
            container_name = f"gsd-worker-{name_suffix}" if name_suffix else None
            
            # Prepare Environment
            env = environment or {}
            
            # Inject Worker DB Config from settings
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
                
                "REDIS_HOST": settings.REDIS_HOST, # Workers typically use same Redis host
                "REDIS_PORT": str(settings.REDIS_PORT),
                "REDIS_PASSWORD": settings.REDIS_PASSWORD,
                # Workers might need different DB, usually 0 for cache, 1 for status
                # But sync_service uses settings.REDIS_DB which defaults to 0
            })
            
            # Mounts - assumes running on host where libs/gsd-shared is available
            # In production, gsd-worker image should have libs installed.
            # In this dev setup, we might need to mount if we want live code, 
            # but gsd-worker image COPYs code. So no mount needed for code.
            # BUT, we might need to pass network config.
            
            logger.info(f"🐳 Spawning worker: {image} cmd={command}")
            
            container = self.client.containers.run(
                image=image,
                command=command,
                detach=True,
                environment=env,
                network_mode="host" if settings.WORKER_NETWORK == "host" else None,
                network=settings.WORKER_NETWORK if settings.WORKER_NETWORK != "host" else None,
                name=container_name,
                auto_remove=False  # Keep container for log inspection
            )
            
            logger.info(f"✅ Started container {container.short_id} ({container.name})")
            return container.id
            
        except Exception as e:
            logger.error(f"❌ Failed to run worker: {e}")
            raise

    def wait_for_container(self, container_id: str) -> dict:
        """
        Wait for container to finish
        Returns: {'StatusCode': int, 'Error': ...}
        """
        try:
            container = self.client.containers.get(container_id)
            result = container.wait()
            return result
        except Exception as e:
            logger.error(f"❌ Failed to wait for container {container_id}: {e}")
            raise

