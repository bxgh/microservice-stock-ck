import logging
import asyncio
from typing import List, Dict, Set, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from core.monitoring import metrics
from core.notifier import notifier

logger = logging.getLogger(__name__)

@dataclass
class Task:
    id: str
    name: str
    command: List[str]
    image: Optional[str] = None
    environment: Dict[str, str] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    
    status: str = "pending"
    container_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None

class Workflow:
    def __init__(self, name: str, tasks: List[Task]):
        self.name = name
        self.tasks = {t.id: t for t in tasks}
        self.validate()
        
    def validate(self) -> None:
        for task in self.tasks.values():
            for dep_id in task.dependencies:
                if dep_id not in self.tasks:
                    raise ValueError(f"Task {task.id} depends on unknown task {dep_id}")
                    
    def get_ready_tasks(self) -> List[Task]:
        ready = []
        for task in self.tasks.values():
            if task.status != "pending":
                continue
                
            deps_met = True
            for dep_id in task.dependencies:
                dep_task = self.tasks[dep_id]
                if dep_task.status != "success":
                    deps_met = False
                    break
            
            if deps_met:
                ready.append(task)
        return ready

    def is_complete(self) -> bool:
        return all(t.status in ["success", "failed", "skipped"] for t in self.tasks.values())
        
    def is_successful(self) -> bool:
        return all(t.status == "success" for t in self.tasks.values())

class DAGEngine:
    def __init__(self, docker_executor):
        self.executor = docker_executor
        
    async def run_workflow(self, workflow: Workflow) -> bool:
        """Run workflow until complete"""
        logger.info(f"🚀 Starting workflow: {workflow.name}")
        start_time = datetime.now()
        
        active_tasks = []
        workflow_status = "unknown"
        
        try:
            while not workflow.is_complete():
                ready_tasks = workflow.get_ready_tasks()
                
                for task in ready_tasks:
                    task.status = "scheduled" 
                    t = asyncio.create_task(self._run_task(task))
                    active_tasks.append(t)
                
                if not ready_tasks and not [t for t in workflow.tasks.values() if t.status in ["scheduled", "running"]]:
                     if not workflow.is_complete():
                         logger.error("Workflow stuck/deadlock!")
                         workflow_status = "failed"
                         await notifier.send_alert("Workflow Deadlock", f"Workflow {workflow.name} is stuck.")
                         break
                
                await asyncio.sleep(1)
                
            if active_tasks:
                await asyncio.gather(*active_tasks, return_exceptions=True)
                
            workflow_status = "success" if workflow.is_successful() else "failed"
            logger.info(f"🏁 Workflow {workflow.name} finished. Success: {workflow.is_successful()}")
            
        except Exception as e:
            logger.error(f"❌ Workflow execution error: {e}")
            workflow_status = "failed"
            await notifier.send_alert("Workflow Error", f"Workflow {workflow.name} failed: {e}")
            
        finally:
            duration = (datetime.now() - start_time).total_seconds()
            metrics.workflow_duration.labels(workflow_name=workflow.name, status=workflow_status).observe(duration)
            metrics.workflow_status.labels(workflow_name=workflow.name, status=workflow_status).inc()
            
        return workflow.is_successful()

    async def _run_task(self, task: Task) -> None:
        """Run a single task using executor"""
        logger.info(f"▶ Running task: {task.name} ({task.id})")
        task.status = "running"
        task.start_time = datetime.now()
        metrics.active_workers.inc()
        
        try:
            container_id = self.executor.run_worker(
                command=task.command,
                environment=task.environment,
                name_suffix=f"{task.id}-{int(datetime.now().timestamp())}"
            )
            task.container_id = container_id
            
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self.executor.wait_for_container, container_id)
            
            status_code = result.get('StatusCode', 1)
            
            task.end_time = datetime.now()
            if status_code == 0:
                task.status = "success"
                logger.info(f"✅ Task {task.id} succeeded")
            else:
                task.status = "failed"
                task.error = f"Exit code: {status_code}"
                logger.error(f"❌ Task {task.id} failed with exit code {status_code}")
                await notifier.send_alert("Task Failed", f"Task {task.name} ({task.id}) failed with exit code {status_code}")

        except Exception as e:
            logger.error(f"❌ Task {task.id} execution error: {e}")
            task.status = "failed"
            task.error = str(e)
            task.end_time = datetime.now()
            await notifier.send_alert("Task Error", f"Task {task.name} ({task.id}) errored: {e}")
            
        finally:
            metrics.active_workers.dec()
            duration = (datetime.now() - task.start_time).total_seconds()
            metrics.task_duration.labels(task_name=task.name, status=task.status).observe(duration)
            metrics.task_status.labels(task_name=task.name, status=task.status).inc()
            
            # Auto cleanup
            if task.container_id:
                try:
                    # In a production system, we might want to keep failed containers for a bit or log them out.
                    # Here we aggressively clean up to save space, assuming logs are captured or forwarded.
                    # Note: We already waited for it, so it's stopped.
                    container = self.executor.client.containers.get(task.container_id)
                    container.remove(force=True)
                    logger.info(f"🗑️ Removed container {task.container_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to remove container {task.container_id}: {e}")
