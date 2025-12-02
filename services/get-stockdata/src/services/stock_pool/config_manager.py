"""
Stock Pool Configuration Manager

Provides unified configuration management for stock pools with:
- Hot reload capability (file watcher)
- Validation and error handling
- Callback system for config change notifications
- Enhanced blacklist/whitelist with rule-based filtering
"""
import asyncio
import json
import logging
import time
import yaml
import fnmatch
from pathlib import Path
from typing import Callable, List, Dict, Any, Optional
from datetime import datetime
from zoneinfo import ZoneInfo

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)


class ConfigChangeHandler(FileSystemEventHandler):
    """配置文件变更监听器"""
    
    def __init__(self, callback: Callable[[str], None]):
        super().__init__()
        self.callback = callback
        self.last_modified = 0
    
    def on_modified(self, event):
        """文件修改事件处理"""
        if event.is_directory:
            return
        
        # 只处理YAML文件
        if not event.src_path.endswith(('.yaml', '.yml')):
            return
        
        # 防抖：1秒内只触发一次（避免编辑器多次保存触发）
        now = time.time()
        if now - self.last_modified < 1.0:
            return
        
        self.last_modified = now
        logger.info(f"🔔 检测到配置文件变更: {event.src_path}")
        
        # 调用回调函数
        self.callback(event.src_path)


class StockPoolConfigManager:
    """
    股票池配置管理器
    
    功能:
    - 加载和验证YAML配置
    - 文件监听和热重载
    - 配置变更回调通知
    - 黑名单/白名单检查
    - 规则过滤支持
    """
    
    def __init__(self, config_path: str = "config/stock_pools_unified.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.config_version: str = ""
        self.config_updated_at: Optional[datetime] = None
        
        # 文件监听
        self.observer: Optional[Observer] = None
        self._watching = False
        
        # 回调函数列表（配置变更时通知）
        self.reload_callbacks: List[Callable] = []
        
        # 线程安全锁
        self._lock = asyncio.Lock()
        
        logger.info(f"📁 ConfigManager initialized with path: {self.config_path}")
    
    async def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            dict: 配置字典
            
        Raises:
            ValueError: 初始加载失败且无旧配置时
        """
        async with self._lock:
            try:
                if not self.config_path.exists():
                    # 如果unified配置不存在，尝试使用旧配置
                    old_config_path = self.config_path.parent / "stock_pools.yaml"
                    if old_config_path.exists():
                        logger.warning(f"⚠️ {self.config_path.name} 不存在，使用旧配置: {old_config_path.name}")
                        self.config_path = old_config_path
                    else:
                        raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
                
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    new_config = yaml.safe_load(f)
                
                # 验证配置
                self._validate_config(new_config)
                
                # 更新配置
                self.config = new_config
                self.config_version = new_config.get('version', 'unknown')
                
                # 解析updated_at时间
                updated_at_str = new_config.get('updated_at')
                if updated_at_str:
                    try:
                        self.config_updated_at = datetime.fromisoformat(updated_at_str)
                        if self.config_updated_at.tzinfo is None:
                            self.config_updated_at = self.config_updated_at.replace(
                                tzinfo=ZoneInfo("Asia/Shanghai")
                            )
                    except Exception as e:
                        logger.warning(f"解析updated_at失败: {e}")
                
                logger.info(f"✅ 配置加载成功 - 版本: {self.config_version}")
                return self.config
                
            except Exception as e:
                logger.error(f"❌ 配置加载失败: {e}")
                
                # 如果是初次加载失败，抛出异常
                if not self.config:
                    raise ValueError(f"初始配置加载失败，无法启动: {e}")
                
                # 否则保留旧配置
                logger.warning("⚠️ 保留旧配置继续运行")
                return self.config
    
    def _validate_config(self, config: Dict[str, Any]):
        """
        验证配置文件格式
        
        Args:
            config: 配置字典
            
        Raises:
            ValueError: 配置格式错误
        """
        # 基本字段检查
        required_fields = ['version']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"配置文件缺少必需字段: {field}")
        
        # 如果有active_mode字段，验证其值
        if 'active_mode' in config:
            valid_modes = ['hs300_top100', 'hot_sectors', 'custom']
            if config['active_mode'] not in valid_modes:
                raise ValueError(
                    f"无效的 active_mode: {config['active_mode']}, "
                    f"有效值: {valid_modes}"
                )
        
        # 验证global配置
        if 'global' in config:
            global_cfg = config['global']
            if 'default_acquisition_interval' in global_cfg:
                interval = global_cfg['default_acquisition_interval']
                if not isinstance(interval, (int, float)) or interval <= 0:
                    raise ValueError(f"无效的 default_acquisition_interval: {interval}")
        
        logger.debug("✅ 配置验证通过")
    
    def start_watching(self):
        """启动配置文件监听"""
        if self._watching:
            logger.warning("⚠️ 文件监听已在运行")
            return
        
        try:
            handler = ConfigChangeHandler(self._on_config_changed)
            self.observer = Observer()
            self.observer.schedule(
                handler,
                path=str(self.config_path.parent),
                recursive=False
            )
            self.observer.start()
            self._watching = True
            logger.info(f"👁️ 配置文件监听已启动: {self.config_path.parent}")
        except Exception as e:
            logger.error(f"❌ 启动文件监听失败: {e}")
    
    def stop_watching(self):
        """停止配置文件监听"""
        if not self._watching or not self.observer:
            return
        
        try:
            self.observer.stop()
            self.observer.join(timeout=5)
            self._watching = False
            logger.info("⏹️ 配置文件监听已停止")
        except Exception as e:
            logger.error(f"❌ 停止文件监听失败: {e}")
    
    def _on_config_changed(self, file_path: str):
        """
        配置文件变更回调（由watchdog触发）
        
        Args:
            file_path: 变更的文件路径
        """
        logger.info(f"📝 配置文件已变更，准备重新加载: {file_path}")
        
        try:
            # 创建异步任务重新加载配置
            asyncio.create_task(self.reload_config())
        except Exception as e:
            logger.error(f"❌ 创建重载任务失败: {e}")
    
    async def reload_config(self):
        """重新加载配置并通知所有监听者"""
        old_version = self.config_version
        
        try:
            # 重新加载配置
            await self.load_config()
            
            logger.info(f"🔄 配置已重新加载: {old_version} -> {self.config_version}")
            
            # 通知所有监听者
            for callback in self.reload_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(self.config)
                    else:
                        callback(self.config)
                except Exception as e:
                    logger.error(f"❌ 配置变更回调失败: {e}")
                    
        except Exception as e:
            logger.error(f"❌ 配置重新加载失败，保持旧配置: {e}")
    
    def register_reload_callback(self, callback: Callable):
        """
        注册配置重载回调
        
        Args:
            callback: 回调函数，接收新配置作为参数
        """
        self.reload_callbacks.append(callback)
        logger.debug(f"✅ 注册配置重载回调: {callback.__name__}")
    
    def get_active_pool_config(self) -> Dict[str, Any]:
        """
        获取当前激活的股票池配置
        
        Returns:
            dict: 当前股票池配置
        """
        mode = self.config.get('active_mode', 'hs300_top100')
        return self.config.get(mode, {})
    
    def is_blacklisted(self, code: str, stock_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        检查股票是否在黑名单中
        
        Args:
            code: 股票代码
            stock_info: 股票信息字典（可选），用于规则匹配
            
        Returns:
            bool: True表示在黑名单中，应过滤掉
        """
        blacklist_cfg = self.config.get('blacklist', {})
        
        # 黑名单未启用
        if not blacklist_cfg.get('enabled', False):
            return False
        
        # 1. 检查白名单（优先级最高）
        whitelist_cfg = self.config.get('whitelist', {})
        if whitelist_cfg.get('enabled', False):
            if code in whitelist_cfg.get('codes', []):
                logger.debug(f"✅ 股票 {code} 在白名单中，不过滤")
                return False
        
        # 2. 检查手动黑名单代码
        if code in blacklist_cfg.get('codes', []):
            logger.debug(f"🚫 股票 {code} 在黑名单代码列表中")
            return True
        
        # 3. 检查模式匹配（股票名称）
        if stock_info:
            stock_name = stock_info.get('名称', stock_info.get('name', ''))
            for pattern in blacklist_cfg.get('patterns', []):
                if fnmatch.fnmatch(stock_name, pattern):
                    logger.debug(f"🚫 股票 {code} ({stock_name}) 匹配黑名单模式: {pattern}")
                    return True
        
        # 4. 检查规则过滤
        if stock_info:
            for rule in blacklist_cfg.get('rules', []):
                field = rule.get('field')
                operator = rule.get('operator')
                value = rule.get('value')
                
                if not all([field, operator, value is not None]):
                    continue
                
                stock_value = stock_info.get(field)
                if stock_value is None:
                    continue
                
                # 应用规则
                if operator == '<' and stock_value < value:
                    logger.debug(
                        f"🚫 股票 {code} 被规则过滤: {field}({stock_value}) < {value}"
                    )
                    return True
                elif operator == '>' and stock_value > value:
                    logger.debug(
                        f"🚫 股票 {code} 被规则过滤: {field}({stock_value}) > {value}"
                    )
                    return True
                elif operator == '==' and stock_value == value:
                    logger.debug(
                        f"🚫 股票 {code} 被规则过滤: {field}({stock_value}) == {value}"
                    )
                    return True
        
        return False
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要信息
        
        Returns:
            dict: 配置摘要
        """
        return {
            'version': self.config_version,
            'updated_at': self.config_updated_at.isoformat() if self.config_updated_at else None,
            'active_mode': self.config.get('active_mode'),
            'blacklist_enabled': self.config.get('blacklist', {}).get('enabled', False),
            'whitelist_enabled': self.config.get('whitelist', {}).get('enabled', False),
            'watching': self._watching,
            'config_path': str(self.config_path)
        }


# 全局单例（可选）
_config_manager: Optional[StockPoolConfigManager] = None


def get_config_manager() -> StockPoolConfigManager:
    """获取全局配置管理器单例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = StockPoolConfigManager()
    return _config_manager
