from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum

class StepType(str, Enum):
    DOCKER = "docker"
    HTTP = "http"
    PARALLEL = "parallel"
    AGENT_DECISION = "agent"

class RetryPolicy(str, Enum):
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    AGENTIC = "agentic"

class WorkflowStep(BaseModel):
    id: str
    task_id: Optional[str] = None
    name: Optional[str] = None
    type: StepType
    command: Optional[List[str]] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    
    # Context Mapping
    outputs: List[Dict[str, str]] = Field(default_factory=list) # [{name: x, path: y}]
    
    # Retry Logic
    retry_policy: RetryPolicy = RetryPolicy.FIXED
    max_attempts: int = 3
    
    # Parallel Strategy (for type=parallel)
    map_from: Optional[str] = None # JSONPath
    template: Optional[Dict[str, Any]] = None

class WorkflowDefinition(BaseModel):
    id: str
    name: str
    version: str = "1.0"
    steps: List[WorkflowStep]
    global_context: Dict[str, Any] = Field(default_factory=dict)

class WorkflowParser:
    """Parser for Workflow 4.0 YAML definitions"""
    
    @staticmethod
    def parse_yaml(content: str) -> WorkflowDefinition:
        import yaml
        data = yaml.safe_load(content)
        if "workflow" in data:
            return WorkflowDefinition.model_validate(data["workflow"])
        return WorkflowDefinition.model_validate(data)

    @staticmethod
    def parse_file(file_path: str) -> WorkflowDefinition:
        with open(file_path, 'r', encoding='utf-8') as f:
            return WorkflowParser.parse_yaml(f.read())
