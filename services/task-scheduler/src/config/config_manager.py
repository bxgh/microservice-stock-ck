"""
配置管理器
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/taskscheduler.yaml"
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        config_file = Path(self.config_path)

        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f"Configuration loaded from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load configuration: {e}")
                self._config = {}
        else:
            logger.warning(f"Configuration file not found: {self.config_path}")
            self._config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def reload(self):
        """重新加载配置"""
        self._load_config()

    def save(self):
        """保存配置到文件"""
        config_file = Path(self.config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")

    def get_database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return self.get('database', {})

    def get_redis_config(self) -> Dict[str, Any]:
        """获取Redis配置"""
        return self.get('redis', {})

    def get_scheduler_config(self) -> Dict[str, Any]:
        """获取调度器配置"""
        return self.get('scheduler', {})

    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """获取插件配置"""
        return self.get(f'plugins.{plugin_name}', {})


# 全局配置管理器实例
config_manager = ConfigManager()