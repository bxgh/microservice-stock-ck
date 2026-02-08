"""
PeerSelector - 同类股筛选器
实现双轨筛选逻辑 (申万行业 + 同花顺概念)
"""
import pandas as pd
import logging
from typing import List, Set, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from dao.industry import IndustryDAO
from dao.stock_info import StockInfoDAO

logger = logging.getLogger(__name__)

# 通用概念黑名单 - 过于宽泛，无区分度
CONCEPT_BLACKLIST = {
    "科创板", "创业板", "主板", "北交所",
    "融资融券", "沪股通", "深股通", 
    "MSCI", "富时罗素", "标普道琼斯",
    "注册制", "新股与次新股", "次新股",
    "HS300_", "中证500", "上证50"
}

# 精准概念阈值 (成分股数量)
PRECISE_CONCEPT_MAX_MEMBERS = 50
BROAD_CONCEPT_MIN_MEMBERS = 200

# 上市时间窗口 (天数)
LISTING_DATE_RANGE_DAYS = 365


@dataclass
class PeerSelectionResult:
    """筛选结果"""
    target_code: str
    target_name: str
    target_ths_industry: str
    target_core_concepts: List[str]
    peers: List[str]
    selection_method: str  # 'industry', 'concept', 'both'


class PeerSelector:
    """
    同类股筛选器
    
    筛选逻辑:
    1. 同花顺三级行业严格匹配
    2. 核心概念交集筛选 (排除黑名单 + 权重过滤)
    3. 上市时间 ±1年 过滤
    """
    
    def __init__(self):
        self.industry_dao = IndustryDAO()
        self.stock_info_dao = StockInfoDAO()
        self._concept_member_counts: Optional[pd.DataFrame] = None
    
    async def select_peers(
        self, 
        target_code: str,
        max_peers: int = 20
    ) -> PeerSelectionResult:
        """
        为目标股票筛选同类股
        
        Args:
            target_code: 目标股票代码 (如 688802.SH)
            max_peers: 最大返回数量
            
        Returns:
            PeerSelectionResult
        """
        # 1. 获取目标股信息
        target_meta = await self.stock_info_dao.get_stock_meta([target_code])
        target_name = target_meta.iloc[0].get('name', 'Unknown') if not target_meta.empty else 'Unknown'
        target_industry = await self._get_target_industry(target_code)
        target_concepts = await self._get_target_concepts(target_code)
        
        # 提取上市日期
        target_listing_date = None
        if not target_meta.empty:
            date_str = target_meta.iloc[0].get('listing_date') or target_meta.iloc[0].get('ipo_date')
            if date_str:
                try:
                    target_listing_date = pd.to_datetime(date_str)
                except:
                    pass
        
        logger.info(f"Target {target_code}: industry={target_industry}, concepts={len(target_concepts)}")
        
        # 2. 行业匹配
        industry_peers = await self._match_by_industry(target_code, target_industry)
        
        # 3. 概念匹配
        core_concepts = await self._identify_core_concepts(target_concepts)
        concept_peers = await self._match_by_concepts(target_code, core_concepts)
        
        # 4. 合并去重
        all_peers = set(industry_peers) | set(concept_peers)
        all_peers.discard(target_code)  # 移除目标自身
        
        # 5. 上市时间过滤
        if target_listing_date:
            filtered_peers = await self._filter_by_listing_date(
                list(all_peers), 
                target_listing_date
            )
        else:
            filtered_peers = list(all_peers)
            
        # 确保顺序确定 (对测试友好)
        filtered_peers.sort()
        
        # 6. 限制数量
        final_peers = filtered_peers[:max_peers]
        
        # 确定筛选方式
        if industry_peers and concept_peers:
            method = 'both'
        elif industry_peers:
            method = 'industry'
        else:
            method = 'concept'
        
        logger.info(f"Selected {len(final_peers)} peers for {target_code} (method={method})")
        
        return PeerSelectionResult(
            target_code=target_code,
            target_name=target_name,
            target_ths_industry=target_industry or "",
            target_core_concepts=core_concepts,
            peers=final_peers,
            selection_method=method
        )
    
    async def _get_target_industry(self, code: str) -> Optional[str]:
        """获取目标股的同花顺三级行业"""
        df = await self.industry_dao.get_ths_industry([code])
        if df.empty:
            return None
        return df.iloc[0].get('l3_name')
    
    async def _get_target_concepts(self, code: str) -> List[str]:
        """获取目标股的所有概念"""
        df = await self.industry_dao.get_stock_concepts([code])
        if df.empty:
            return []
        
        concepts = df['sector_name'].tolist()
        # 使用子串检查增强黑名单过滤，并去重
        filtered = []
        for c in concepts:
            if any(black in c for black in CONCEPT_BLACKLIST):
                continue
            if c not in filtered:
                filtered.append(c)
        return filtered
    
    async def _get_listing_date(self, code: str) -> Optional[datetime]:
        """获取上市日期"""
        df = await self.stock_info_dao.get_stock_meta([code])
        if df.empty:
            return None
        # 假设有 listing_date 字段
        date_str = df.iloc[0].get('listing_date') or df.iloc[0].get('ipo_date')
        if date_str:
            try:
                return pd.to_datetime(date_str)
            except Exception:
                return None
        return None
    
    async def _match_by_industry(self, target_code: str, industry: Optional[str]) -> List[str]:
        """按同花顺三级行业匹配"""
        if not industry:
            return []
        
        # 调用 IndustryDAO 的反向查询方法 (需扩展)
        # 暂时使用直接的 gRPC 调用
        try:
            from dao.client import data_client
            from datasource.v1 import data_source_pb2
            
            # 使用特殊参数进行反向查询
            df = await data_client.fetch_data(
                data_source_pb2.DATA_TYPE_THS_INDUSTRY,
                ["*"],  # 通配符表示反向查询
                params={"l3_name": industry}
            )
            if df.empty:
                return []
            return df['ts_code'].tolist()
        except Exception as e:
            logger.warning(f"Industry matching failed: {e}")
            return []
    
    async def _identify_core_concepts(self, concepts: List[str]) -> List[str]:
        """识别核心概念 (成分股少的优先)"""
        if not concepts:
            return []
        
        # 未来可以调用 get_concept_member_counts 进行排序
        # 暂时简单取前3个非黑名单概念
        filtered = [c for c in concepts if c not in CONCEPT_BLACKLIST]
        return filtered[:3]
    
    async def _match_by_concepts(self, target_code: str, core_concepts: List[str]) -> List[str]:
        """按核心概念匹配"""
        if not core_concepts:
            return []
        
        try:
            from dao.client import data_client
            from datasource.v1 import data_source_pb2
            
            all_peers = set()
            for concept in core_concepts:
                # 使用特殊参数进行概念成分查询
                df = await data_client.fetch_data(
                    data_source_pb2.DATA_TYPE_THS_CONCEPTS,
                    ["*"],  # 通配符表示反向查询
                    params={"concept_name": concept}
                )
                if not df.empty and 'ts_code' in df.columns:
                    all_peers.update(df['ts_code'].tolist())
            return list(all_peers)
        except Exception as e:
            logger.warning(f"Concept matching failed: {e}")
            return []
    
    async def _filter_by_listing_date(
        self, 
        codes: List[str], 
        target_date: datetime
    ) -> List[str]:
        """按上市时间过滤 (±1年)"""
        if not codes:
            return []
        
        df = await self.stock_info_dao.get_stock_meta(codes)
        if df.empty:
            return codes  # 无法过滤，返回全部
        
        min_date = target_date - timedelta(days=LISTING_DATE_RANGE_DAYS)
        max_date = target_date + timedelta(days=LISTING_DATE_RANGE_DAYS)
        
        filtered = []
        for _, row in df.iterrows():
            date_str = row.get('listing_date') or row.get('ipo_date')
            if date_str:
                try:
                    listing_date = pd.to_datetime(date_str)
                    if min_date <= listing_date <= max_date:
                        filtered.append(row.get('code') or row.get('ts_code'))
                except Exception:
                    continue
        
        return filtered
