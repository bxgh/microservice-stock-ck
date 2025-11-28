from enum import Enum
from typing import List, Set, Dict
from datetime import datetime
import akshare as ak
import pandas as pd
from pydantic import BaseModel

class PoolLevel(Enum):
    L1_CORE = "L1_CORE"       # 核心池 (3秒/次)
    L2_ACTIVE = "L2_ACTIVE"   # 活跃池 (15秒/次)
    L3_UNIVERSE = "L3_UNIVERSE" # 全市场 (1分钟/次)

class StockPoolConfig(BaseModel):
    name: str
    level: PoolLevel
    symbols: Set[str]
    last_update: datetime

class StockPoolManager:
    """
    股票池管理器
    负责维护不同层级的股票列表
    """
    
    def __init__(self):
        self.pools: Dict[PoolLevel, StockPoolConfig] = {
            PoolLevel.L1_CORE: StockPoolConfig(
                name="Core Assets", 
                level=PoolLevel.L1_CORE, 
                symbols=set(), 
                last_update=datetime.min
            ),
            PoolLevel.L2_ACTIVE: StockPoolConfig(
                name="Active Assets", 
                level=PoolLevel.L2_ACTIVE, 
                symbols=set(), 
                last_update=datetime.min
            ),
            PoolLevel.L3_UNIVERSE: StockPoolConfig(
                name="Market Universe", 
                level=PoolLevel.L3_UNIVERSE, 
                symbols=set(), 
                last_update=datetime.min
            )
        }
    
    def initialize_static_l1_pool(self) -> int:
        """
        初始化静态L1池 (沪深300)
        
        Returns:
            int: 池中股票数量
        """
        print("🔄 Initializing Static L1 Pool (CSI 300)...")
        try:
            # 获取沪深300成分股
            # akshare接口: index_stock_cons_weight_csindex(symbol="000300")
            # 或者 stock_zh_index_spot 找沪深300
            
            # 使用更稳定的接口获取成分股
            # 注意：akshare接口变动频繁，这里使用 index_stock_cons
            df = ak.index_stock_cons(symbol="000300")
            
            if df is None or df.empty:
                print("⚠️ Failed to fetch CSI 300 data")
                return 0
                
            # 提取股票代码
            # akshare返回的通常是 '600000' 格式，我们需要统一格式
            # 假设我们需要 '600000' 格式
            symbols = set(df['品种代码'].tolist())
            
            self.pools[PoolLevel.L1_CORE].symbols = symbols
            self.pools[PoolLevel.L1_CORE].last_update = datetime.now()
            
            print(f"✅ L1 Pool Initialized: {len(symbols)} stocks")
            return len(symbols)
            
        except Exception as e:
            print(f"❌ Error initializing L1 pool: {e}")
            return 0

    def get_pool_symbols(self, level: PoolLevel) -> List[str]:
        """获取指定池的股票列表"""
        return list(self.pools[level].symbols)

    def add_custom_to_l1(self, symbols: List[str]):
        """添加自选股到L1池"""
        current = self.pools[PoolLevel.L1_CORE].symbols
        current.update(symbols)
        self.pools[PoolLevel.L1_CORE].symbols = current
        print(f"➕ Added {len(symbols)} custom stocks to L1. Total: {len(current)}")

if __name__ == "__main__":
    # 测试代码
    manager = StockPoolManager()
    count = manager.initialize_static_l1_pool()
    print(f"L1 Pool Size: {count}")
    
    # 打印前5个
    l1_symbols = manager.get_pool_symbols(PoolLevel.L1_CORE)
    print(f"Sample: {l1_symbols[:5]}")
