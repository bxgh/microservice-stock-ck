"""
插件系统模块
"""

from .plugin_manager import PluginManager
from .base_plugin import BasePlugin

__all__ = ["PluginManager", "BasePlugin"]