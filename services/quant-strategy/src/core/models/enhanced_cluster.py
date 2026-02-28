from enum import Enum
from pydantic import BaseModel, ConfigDict # type: ignore
from typing import List

class TrendPhase(str, Enum):
    FORMATION = "合力形成期"
    STEADY = "稳定运行期"
    DISSOLUTION = "瓦解期"

class EnhancedCluster(BaseModel):
    """
    附带微观领导力分析增强的资产聚类模型
    包含了从 TLCC 及 PageRank 中挖掘出的龙头信息，以及由标准差得出的群体走势阶段
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # 继承或复制的基础属性
    cluster_id: int
    stock_codes: List[str]
    member_count: int
    dominant_industry: str
    
    # 微观增强属性
    leader_stock: str
    pagerank_score: float
    current_divergence: float
    trend_phase: TrendPhase
    
    def __str__(self) -> str:
        return (f"<EnhancedCluster #{self.cluster_id} | Members: {self.member_count} | "
                f"Leader: {self.leader_stock} (PR: {self.pagerank_score:.3f}) | Phase: {self.trend_phase.value}>")
