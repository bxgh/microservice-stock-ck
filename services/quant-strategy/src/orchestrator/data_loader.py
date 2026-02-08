"""
DataLoader - 数据加载器
负责为策略编排器统一加载目标股及其同类股的所有必需数据
"""
import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from dao.feature_store import FeatureStoreDAO
from dao.kline import KLineDAO

logger = logging.getLogger(__name__)

class DataLoader:
    """
    统一数据加载器
    负责获取目标股(Target)与同类股(Peers)的特征矩阵
    """
    
    def __init__(self):
        self.feature_dao = FeatureStoreDAO()
        self.kline_dao = KLineDAO()
        
    async def load_strategy_data(
        self,
        target_code: str,
        peer_codes: List[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """
        加载策略执行所需的所有数据 (优先从 Redis 特征仓库加载)
        """
        logger.info(f"Loading data: target={target_code}, peers={len(peer_codes)}, range={start_date}~{end_date}")
        
        from cache.feature_store import FeatureStore
        store = FeatureStore()
        
        # 1. 尝试从 Redis 批量获取 (针对最新日期优化)
        # 注意: 目前 FeatureStore 只存储单日矩阵，我们取 end_date 这一天进行对标分析
        all_codes = [target_code] + peer_codes
        redis_feats = await store.batch_get(all_codes, end_date)
        
        def matrix_to_df(code, date, matrix):
            if matrix is None or matrix.size == 0:
                return pd.DataFrame()
            # 矩阵 shape (240, 9), 我们取其平均值或特征汇总作为日指标
            # 或者如果是 9x1 也可以，StrategyFactory 存的是 main_df.to_numpy()
            # 根据 StrategyFactory.compute_and_store, 存的是 240x9 的对齐矩阵
            # 我们在这里聚合为日线级别的 9 维特征 (取均值)
            mean_vals = np.mean(matrix, axis=0)
            data = {f'f{i+1}': [mean_vals[i]] for i in range(9)}
            data['ts_code'] = [code]
            data['trade_date'] = [date]
            return pd.DataFrame(data)

        import numpy as np
        
        # 2. 如果 Redis 有数据，直接构造 DF
        target_df = pd.DataFrame()
        peers_df_list = []
        
        if target_code in redis_feats:
            target_df = matrix_to_df(target_code, end_date, redis_feats[target_code])
            logger.info(f"✅ Loaded target {target_code} from Redis Cache")
            
        for p_code in peer_codes:
            if p_code in redis_feats:
                peers_df_list.append(matrix_to_df(p_code, end_date, redis_feats[p_code]))
        
        # 3. 兜底: 如果 Redis 没数据，从 ClickHouse (RPC) 加载
        if target_df.empty:
            target_df = await self.feature_dao.get_features([target_code], start_date, end_date)
            
        missing_peers = [c for c in peer_codes if c not in redis_feats]
        if missing_peers:
            ch_peers_df = await self.feature_dao.get_features(missing_peers, start_date, end_date)
            if not ch_peers_df.empty:
                peers_df_list.append(ch_peers_df)

        peers_df = pd.concat(peers_df_list, ignore_index=True) if peers_df_list else pd.DataFrame()
        
        if target_df.empty:
            logger.warning(f"Target stock {target_code} features are empty")
        if peers_df.empty and peer_codes:
            logger.warning(f"Peer stocks features are empty for {len(peer_codes)} codes")
            
        # 4. 格式化日期
        for df in [target_df, peers_df]:
            if not df.empty and 'trade_date' in df.columns:
                df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        return {
            "target": target_df,
            "peers": peers_df
        }

    async def get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """获取时间范围内的交易日列表 (辅助对齐)"""
        # 可以通过 000001.SH 指数获取
        df = await self.kline_dao.get_kline(["000001.SH"], start_date, end_date)
        if df.empty:
            return []
        return df['trade_date'].dt.strftime('%Y-%m-%d').tolist()
