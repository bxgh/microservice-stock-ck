import logging
import docker
from typing import Dict, List, Optional, Any
from config.settings import settings

logger = logging.getLogger(__name__)

class DockerExecutor:
    """Docker Container Executor"""
    
    def __init__(self, client: docker.DockerClient):
        self.client = client
        
    def run_worker(self, 
                   command: List[str], 
                   environment: Optional[Dict[str, str]] = None,
                   volumes: Optional[Dict[str, Any]] = None,
                   input_context: Optional[str] = None,
                   name_suffix: str = "",
                   network_mode: Optional[str] = None) -> str:
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
                
                # Also inject with GSD_ prefix for compatibility (e.g. DataQualityService)
                "GSD_DB_HOST": settings.WORKER_MYSQL_HOST,
                "GSD_DB_PORT": str(settings.WORKER_MYSQL_PORT),
                "GSD_DB_USER": settings.WORKER_MYSQL_USER,
                "GSD_DB_PASSWORD": settings.WORKER_MYSQL_PASSWORD,
                "GSD_DB_NAME": settings.WORKER_MYSQL_DATABASE,
                
                "CLICKHOUSE_HOST": settings.WORKER_CLICKHOUSE_HOST,
                "CLICKHOUSE_PORT": str(settings.WORKER_CLICKHOUSE_PORT),
                "CLICKHOUSE_USER": settings.WORKER_CLICKHOUSE_USER,
                "CLICKHOUSE_PASSWORD": settings.WORKER_CLICKHOUSE_PASSWORD,
                "CLICKHOUSE_DATABASE": settings.WORKER_CLICKHOUSE_DATABASE,
                
                "GSD_CLICKHOUSE_HOST": settings.WORKER_CLICKHOUSE_HOST,
                "GSD_CLICKHOUSE_PORT": str(settings.WORKER_CLICKHOUSE_PORT),
                "GSD_CLICKHOUSE_USER": settings.WORKER_CLICKHOUSE_USER,
                "GSD_CLICKHOUSE_PASSWORD": settings.WORKER_CLICKHOUSE_PASSWORD,
                "GSD_CLICKHOUSE_DATABASE": settings.WORKER_CLICKHOUSE_DATABASE,
                
                "REDIS_HOST": settings.REDIS_HOST,
                "REDIS_PORT": str(settings.REDIS_PORT),
                "REDIS_PASSWORD": settings.REDIS_PASSWORD,
                "REDIS_CLUSTER": str(settings.REDIS_CLUSTER).lower(),
                "MOOTDX_API_URL": settings.WORKER_MOOTDX_API_URL,
                "GSD_REDIS_URL": f"redis://{':' + settings.REDIS_PASSWORD + '@' if settings.REDIS_PASSWORD else ''}{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                "GSD_INPUT_CONTEXT": input_context or "{}"
            })
            
            # Ensure PYTHONPATH includes gsd-agent if mapped
            env["PYTHONPATH"] = "/app/src:/app/libs/gsd-shared:/app/libs/gsd-agent"
            
            # Prepare volumes mount
            vols = volumes
            if not vols:
                vols = {
                    f'{settings.HOST_BASE_DIR}/data/gsd-worker': {'bind': '/app/data', 'mode': 'rw'},
                    f'{settings.HOST_BASE_DIR}/libs/gsd-shared': {'bind': '/app/libs/gsd-shared', 'mode': 'ro'},
                    f'{settings.HOST_BASE_DIR}/libs/gsd-agent/src': {'bind': '/app/libs/gsd-agent', 'mode': 'ro'},
                    f'{settings.HOST_BASE_DIR}/services/gsd-worker/config': {'bind': '/app/config', 'mode': 'ro'},
                    f'{settings.HOST_BASE_DIR}/services/gsd-worker/src': {'bind': '/app/src', 'mode': 'ro'}
                }

            # Determine Network Mode: Task Specific > Global Setting
            final_network_mode = network_mode or (
                "host" if settings.WORKER_NETWORK == "host" else None
            )

            container = self.client.containers.run(
                image=image,
                command=command,
                detach=True,
                environment=env,
                network_mode=final_network_mode,
                network=settings.WORKER_NETWORK if final_network_mode != "host" else None,
                name=container_name,
                volumes=vols,
                auto_remove=False,  # Keep container for log inspection
                tty=True            # Use TTY to get clean logs (no 8-byte headers)
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

