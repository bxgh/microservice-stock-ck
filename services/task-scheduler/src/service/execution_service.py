"""
任务执行服务
"""

import logging
from typing import Dict, Any
from plugins.plugin_manager import PluginManager

logger = logging.getLogger(__name__)


class ExecutionService:
    """任务执行服务"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.plugin_manager = PluginManager()

    async def execute_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        try:
            task_type = task_data.get("task_type", "http")
            config = task_data.get("config", {})

            # 根据任务类型执行不同的操作
            if task_type == "http":
                result = await self._execute_http_task(config)
            elif task_type == "shell":
                result = await self._execute_shell_task(config)
            else:
                # 使用插件管理器执行自定义插件
                result = await self.plugin_manager.execute_plugin(
                    task_type, config, task_data
                )

            return {
                "success": True,
                "result": result,
                "message": "Task executed successfully"
            }
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Task execution failed"
            }

    async def _execute_http_task(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """执行HTTP任务"""
        import aiohttp

        url = config.get("url", "https://httpbin.org/get")
        method = config.get("method", "GET")
        headers = config.get("headers", {})
        data = config.get("data")
        timeout = config.get("timeout", 30)

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.request(method, url, headers=headers, json=data) as response:
                return {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "body": await response.text(),
                    "url": str(response.url)
                }

    async def _execute_shell_task(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """执行Shell任务"""
        import asyncio

        command = config.get("command", "echo 'Hello World'")
        cwd = config.get("cwd")
        timeout = config.get("timeout", 30)

        try:
            proc = await asyncio.wait_for(
                asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd
                ),
                timeout=timeout
            )

            stdout, stderr = await proc.communicate()

            return {
                "return_code": proc.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "command": command
            }
        except asyncio.TimeoutError:
            return {
                "return_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "command": command
            }