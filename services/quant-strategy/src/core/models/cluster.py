from pydantic import BaseModel, ConfigDict # type: ignore
from typing import List, Dict

class FundCluster(BaseModel):
    """
    主力资金团伙模型
    表示通过时间序列相似度与图聚类发现的一批具备高度同步性异动的股票结合体
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    cluster_id: int
    stock_codes: List[str]
    
    # 元数据/统计参考值
    member_count: int
    dominant_industry: str
    industry_ratio: float
    avg_turnover: float
    beta_correlation: float
    
    def __str__(self) -> str:
        return f"<FundCluster #{self.cluster_id} | Members: {self.member_count} | Dominant: {self.dominant_industry} ({self.industry_ratio*100:.1f}%)>"
