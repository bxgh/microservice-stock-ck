"""
基础插件类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BasePlugin(ABC):
    """插件基类"""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}

    @abstractmethod
    async def execute(self, task_data: Dict[str, Any]) -> Any:
        """执行任务"""
        pass

    @abstractmethod
    def validate(self, task_data: Dict[str, Any]) -> bool:
        """验证任务数据"""
        pass

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证插件配置（默认实现）"""
        return True