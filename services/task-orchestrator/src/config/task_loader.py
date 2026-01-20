"""
任务配置加载器

从 YAML 文件加载任务配置，验证配置有效性，解析环境变量
"""

import os
import yaml
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum

logger = logging.getLogger(__name__)


class ScheduleType(str, Enum):
    """调度类型"""
    CRON = "cron"
    TRADING_CRON = "trading_cron"
    DATE = "date"


class TaskType(str, Enum):
    """任务类型"""
    DOCKER = "docker"
    HTTP = "http"
    WORKFLOW = "workflow"
    COMMAND_EMITTER = "command_emitter"


class ScheduleConfig(BaseModel):
    """调度配置"""
    type: ScheduleType
    expression: Optional[str] = None  # cron表达式
    run_date: Optional[str] = None    # 一次性任务时间


class RetryConfig(BaseModel):
    """重试配置"""
    max_attempts: int = Field(default=1, ge=1, le=10)
    backoff_seconds: int = Field(default=60, ge=0)
    backoff_multiplier: float = Field(default=2.0, ge=1.0)


class DockerTargetConfig(BaseModel):
    """Docker任务目标配置"""
    image: Optional[str] = None
    command: List[str]
    environment: Optional[Dict[str, str]] = None
    volumes: Optional[List[str]] = None
    network_mode: Optional[str] = "host"


class HttpTargetConfig(BaseModel):
    """HTTP任务目标配置"""
    service: Optional[str] = None  # Nacos服务名
    url: Optional[str] = None      # 直接URL
    endpoint: Optional[str] = None # 服务端点
    method: str = "POST"
    timeout_seconds: int = 30
    headers: Optional[Dict[str, str]] = None


class WorkflowStep(BaseModel):
    """工作流步骤"""
    id: str
    command: Optional[List[str]] = None
    parallel: bool = False
    depends_on: Optional[List[str]] = None
    tasks: Optional[List[Dict[str, Any]]] = None  # 并行任务列表


class TaskDefinition(BaseModel):
    """任务定义"""
    id: str
    name: str
    type: TaskType
    enabled: bool = True
    schedule: ScheduleConfig
    target: Optional[Dict[str, Any]] = None
    workflow: Optional[List[WorkflowStep]] = None
    dependencies: Optional[List[str]] = None
    retry: RetryConfig = Field(default_factory=RetryConfig)
    
    @validator('workflow')
    def validate_workflow(cls, v, values):
        """验证workflow类型任务必须有workflow配置"""
        if values.get('type') == TaskType.WORKFLOW and not v:
            raise ValueError("workflow类型任务必须有workflow配置")
        return v


class GlobalConfig(BaseModel):
    """全局配置"""
    docker: Optional[Dict[str, Any]] = None
    notifications: Optional[Dict[str, Any]] = None


class TaskConfig(BaseModel):
    """任务配置根"""
    version: str
    timezone: str = "Asia/Shanghai"
    global_: Optional[GlobalConfig] = Field(None, alias='global')
    tasks: List[TaskDefinition]


class TaskLoader:
    """任务配置加载器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def load_from_yaml(self, path: str) -> TaskConfig:
        """
        从YAML文件加载任务配置
        
        Args:
            path: YAML文件路径
            
        Returns:
            TaskConfig: 解析后的任务配置
        """
        self.logger.info(f"Loading task configuration from {path}")
        
        # 读取YAML文件
        with open(path, 'r', encoding='utf-8') as f:
            raw_config = yaml.safe_load(f)
        
        # 解析环境变量
        resolved_config = self._resolve_env_vars(raw_config)
        
        # 验证并解析配置
        try:
            config = TaskConfig(**resolved_config)
            self.logger.info(f"✓ Loaded {len(config.tasks)} tasks")
            
            # 验证任务依赖
            self._validate_dependencies(config.tasks)
            
            # 验证任务ID唯一性
            self._validate_unique_ids(config.tasks)
            
            return config
        except Exception as e:
            self.logger.error(f"❌ Failed to parse task configuration: {e}")
            raise
    
    def _resolve_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归解析环境变量
        
        支持格式:
        - ${VAR_NAME}
        - ${VAR_NAME:-default_value}
        """
        if isinstance(config, dict):
            return {k: self._resolve_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._resolve_env_vars(item) for item in config]
        elif isinstance(config, str):
            return self._expand_env_var(config)
        else:
            return config
    
    def _expand_env_var(self, value: str) -> str:
        """
        扩展单个环境变量
        
        Examples:
            "${MYSQL_HOST}" -> "127.0.0.1"
            "${MYSQL_HOST:-127.0.0.1}" -> "127.0.0.1" (如果未设置)
        """
        import re
        
        # 匹配 ${VAR_NAME} 或 ${VAR_NAME:-default}
        pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'
        
        def replace_var(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ""
            return os.getenv(var_name, default_value)
        
        return re.sub(pattern, replace_var, value)
    
    def _validate_dependencies(self, tasks: List[TaskDefinition]):
        """验证任务依赖关系"""
        task_ids = {task.id for task in tasks}
        
        for task in tasks:
            if task.dependencies:
                for dep in task.dependencies:
                    if dep not in task_ids:
                        raise ValueError(
                            f"Task '{task.id}' depends on non-existent task '{dep}'"
                        )
        
        # 检测循环依赖
        self._check_circular_dependencies(tasks)
    
    def _check_circular_dependencies(self, tasks: List[TaskDefinition]):
        """检测循环依赖"""
        # 构建依赖图
        graph = {task.id: task.dependencies or [] for task in tasks}
        
        # DFS检测环
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for task_id in graph:
            if task_id not in visited:
                if has_cycle(task_id):
                    raise ValueError(f"Circular dependency detected involving task '{task_id}'")
    
    def _validate_unique_ids(self, tasks: List[TaskDefinition]):
        """验证任务ID唯一性"""
        task_ids = [task.id for task in tasks]
        duplicates = [tid for tid in set(task_ids) if task_ids.count(tid) > 1]
        
        if duplicates:
            raise ValueError(f"Duplicate task IDs found: {duplicates}")
    
    def get_enabled_tasks(self, config: TaskConfig) -> List[TaskDefinition]:
        """获取所有启用的任务"""
        return [task for task in config.tasks if task.enabled]
