import os
import yaml
import logging

class PoolLevel:
    L1_CORE = "L1"
    L2_PREMIUM = "L2"
    L3_ALL = "L3"

class StockPoolManager:
    """
    股票池管理器 (Code Quality Improvement)
    负责加载和管理股票池配置
    """
    def __init__(self, config_manager=None, **kwargs):
        self.logger = logging.getLogger("StockPoolManager")
        self.config_manager = config_manager
        self.config_path = os.getenv('STOCK_POOL_CONFIG', '/app/config/hs300_stocks.yaml')
        self._pool = []
        self._load_config()

    def _load_config(self):
        """加载股票池配置"""
        try:
            if not os.path.exists(self.config_path):
                self.logger.warning(f"⚠️ Config not found at {self.config_path}, using empty pool")
                return

            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self._pool = data.get('stocks', [])
            
            self.logger.info(f"✅ Loaded {len(self._pool)} stocks from {self.config_path}")
        except Exception as e:
            self.logger.error(f"❌ Failed to load stock pool config: {e}")
            self._pool = []

    async def get_current_pool(self):
        """兼容 AcquisitionScheduler 的异步接口"""
        return self._pool

    def get_pool_symbols(self, level: str = PoolLevel.L1_CORE):
        """获取指定级别的股票列表"""
        if level == PoolLevel.L1_CORE:
            return self._pool
        return []

    def initialize_static_l1_pool(self):
        """兼容旧接口"""
        self._load_config()
