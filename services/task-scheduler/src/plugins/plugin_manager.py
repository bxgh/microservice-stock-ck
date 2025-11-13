"""
插件管理器
"""

import importlib
import logging
from typing import Dict, Type, Any, Optional
from .base_plugin import BasePlugin

logger = logging.getLogger(__name__)


class PluginManager:
    """插件管理器"""

    def __init__(self):
        self.plugins: Dict[str, Type[BasePlugin]] = {}
        self._load_default_plugins()

    def _load_default_plugins(self):
        """加载默认插件"""
        # 注册默认的HTTP插件
        self.register_plugin("http", HttpPlugin)
        # 注册默认的Shell插件
        self.register_plugin("shell", ShellPlugin)

    def register_plugin(self, name: str, plugin_class: Type[BasePlugin]):
        """注册插件"""
        self.plugins[name] = plugin_class
        logger.info(f"Plugin '{name}' registered successfully")

    def get_plugin(self, name: str) -> Optional[Type[BasePlugin]]:
        """获取插件类"""
        return self.plugins.get(name)

    def get_available_plugins(self) -> Dict[str, Type[BasePlugin]]:
        """获取所有可用插件"""
        return self.plugins.copy()

    async def execute_plugin(self, plugin_name: str, config: Dict[str, Any], task_data: Dict[str, Any]) -> Any:
        """执行插件"""
        plugin_class = self.get_plugin(plugin_name)
        if not plugin_class:
            raise ValueError(f"Plugin '{plugin_name}' not found")

        plugin = plugin_class(plugin_name, config)

        if not plugin.validate(task_data):
            raise ValueError(f"Task data validation failed for plugin '{plugin_name}'")

        return await plugin.execute(task_data)


class HttpPlugin(BasePlugin):
    """HTTP请求插件"""

    async def execute(self, task_data: Dict[str, Any]) -> Any:
        import aiohttp

        url = task_data.get("url")
        method = task_data.get("method", "GET")
        headers = task_data.get("headers", {})
        data = task_data.get("data")

        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, json=data) as response:
                return {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "body": await response.text()
                }

    def validate(self, task_data: Dict[str, Any]) -> bool:
        return "url" in task_data

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证HTTP插件配置"""
        if not config:
            return False
        if "url" not in config:
            return False
        # 验证HTTP方法
        method = config.get("method", "GET").upper()
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        return method in valid_methods


class ShellPlugin(BasePlugin):
    """Shell命令插件"""

    async def execute(self, task_data: Dict[str, Any]) -> Any:
        import asyncio

        command = task_data.get("command")
        cwd = task_data.get("cwd")

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )

        stdout, stderr = await proc.communicate()

        return {
            "return_code": proc.returncode,
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else ""
        }

    def validate(self, task_data: Dict[str, Any]) -> bool:
        return "command" in task_data

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证Shell插件配置"""
        if not config:
            return False
        if "command" not in config:
            return False
        # 基本安全检查：防止危险命令
        dangerous_commands = ["rm -rf /", "dd if=", "mkfs", "format"]
        command = config.get("command", "").lower()
        for dangerous in dangerous_commands:
            if dangerous in command:
                return False
        return True