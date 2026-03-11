import logging
from typing import Dict, List, Tuple
from src.strategies.geopolitical.constants import ScenarioType, DEFENSIVE_SECTORS
from src.dao.industry import IndustryDAO

logger = logging.getLogger(__name__)

class GeopoliticalScoringService:
    """
    地缘冲突评分服务
    负责根据当前战争情景，为避险板块个股提供加分，并提供动态权重建议。
    """

    def __init__(self):
        self.industry_dao = IndustryDAO()

    def get_dynamic_weights(self, scenario: ScenarioType) -> Tuple[float, float]:
        """
        根据情景返回 (fundamental_weight, valuation_weight)
        
        Scenario C (持久战) 下权重向基本面大幅倾斜。
        """
        if scenario == ScenarioType.SCENARIO_C:
            return 0.8, 0.2
        
        # 默认权重 (Story 2.4 中定义的 0.6 / 0.4)
        return 0.6, 0.4

    async def get_geopolitical_bonuses(
        self, 
        stock_codes: List[str], 
        scenario: ScenarioType
    ) -> Dict[str, Tuple[float, str]]:
        """
        获取避险板块额外加分映射
        
        Returns:
            Dict[str, Tuple[float, str]]: {stock_code: (bonus, reason)}
        """
        if scenario == ScenarioType.IDLE:
            return {}

        bonuses = {}
        # 根据情景确定加分额度
        bonus_value = 0.0
        if scenario == ScenarioType.SCENARIO_A:
            bonus_value = 15.0
        elif scenario == ScenarioType.SCENARIO_B:
            bonus_value = 10.0
        elif scenario == ScenarioType.SCENARIO_C:
            bonus_value = 8.0

        try:
            # 获取股票所属概念板块
            concept_df = await self.industry_dao.get_stock_concepts(stock_codes)
            
            if not concept_df.empty:
                for _, row in concept_df.iterrows():
                    code = row["ts_code"]
                    sector_name = row["sector_name"]
                    
                    # 匹配防御性板块关键字
                    is_defensive = any(keyword in sector_name for keyword in DEFENSIVE_SECTORS)
                    
                    if is_defensive:
                        # 如果该股票有多个概念命中，取最大加分（此处目前加分一致）
                        if code not in bonuses:
                            bonuses[code] = (bonus_value, f"GeopoliticalDefense[{sector_name}]")
                        
        except Exception as e:
            logger.error(f"Failed to calculate geopolitical bonuses: {e}")

        return bonuses
