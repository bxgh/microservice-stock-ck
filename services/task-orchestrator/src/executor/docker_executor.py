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
            # Inject common envs if needed
            
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

