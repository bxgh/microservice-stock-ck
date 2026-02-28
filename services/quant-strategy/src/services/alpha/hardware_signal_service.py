import logging
import pandas as pd
from typing import Dict, List, Tuple
from dao.altdata import AltDataDAO
from config.altdata_mapping import get_concepts_for_label

logger = logging.getLogger(__name__)

class HardwareSignalService:
    """
    硬件信号服务 (Story 18.3)
    将底层硬件遥测数据转换为 A 股板块加分信号。
    """
    
    def __init__(self, alt_dao: AltDataDAO | None = None):
        self.alt_dao = alt_dao or AltDataDAO()
        # 信号权重定义
        self.premium_bonus = 8.0     # 价格大幅上涨加分
        self.pulse_bonus_base = 5.0  # 中标脉冲基础加分
        self.pulse_bonus_large = 12.0 # 极大型中标加分 (>1亿元)

    async def get_hardware_bonuses(self) -> Dict[str, Tuple[float, str]]:
        """
        获取当前有效的硬件信号红利。
        返回: Dict[概念名称, (加分分值, 原因描述)]
        """
        bonuses = {} # type: Dict[str, Tuple[float, str]]
        
        # 1. 获取 GPU 现货溢价信号
        try:
            spot_df = self.alt_dao.get_hardware_spot_stats(lookback_days=7)
            if not spot_df.empty:
                # 简单逻辑：如果某些型号平均价格较高或可用度低，视为需求旺盛
                # 实际上可以对比 7d vs 30d 均价，这里暂做简化阈值判断
                for _, row in spot_df.iterrows():
                    gpu = row["gpu_model"].lower()
                    # 识别型号并映射标签
                    label = self._map_gpu_to_label(gpu)
                    if not label:
                        continue
                        
                    concepts = get_concepts_for_label(label)
                    # 逻辑：只要监控到活跃价格，说明算力需求存在，给予基础加分
                    # 如果有具体涨幅逻辑在此处扩展
                    for fleet_concept in concepts:
                        reason = f"Hardware[Premium:{row['gpu_model']}@{row['platform']}]"
                        if fleet_concept not in bonuses or bonuses[fleet_concept][0] < self.premium_bonus:
                            bonuses[fleet_concept] = (self.premium_bonus, reason)
        except Exception as e:
            logger.error(f"Failed to process hardware spot signals: {e}")

        # 2. 获取政企投资脉冲信号 (CAPEX)
        try:
            capex_df = self.alt_dao.get_procurement_capex_signals(lookback_days=14)
            if not capex_df.empty:
                for _, row in capex_df.iterrows():
                    hw_type = row["hardware_type"].lower()
                    total_amt = row["total_amount"] # 万元
                    
                    concepts = get_concepts_for_label(hw_type)
                    bonus = self.pulse_bonus_base
                    if total_amt > 10000: # 大于 1 亿元
                        bonus = self.pulse_bonus_large
                        
                    for c in concepts:
                        reason = f"Hardware[Capex:{row['hardware_type']} Pulse {total_amt:.0f}W]"
                        if c not in bonuses or bonuses[c][0] < bonus:
                            bonuses[c] = (bonus, reason)
        except Exception as e:
            logger.error(f"Failed to process procurement capex signals: {e}")

        return bonuses

    def _map_gpu_to_label(self, gpu_name: str) -> str | None:
        """模型名称到另类数据标签的模糊映射"""
        gpu_name = gpu_name.lower()
        if any(x in gpu_name for x in ["h100", "a100", "4090", "h800", "a800"]):
            return "nvidia"
        if any(x in gpu_name for x in ["910b", "昇腾", "ascend"]):
            return "ascend"
        if any(x in gpu_name for x in ["c500", "n100", "沐曦", "metax"]):
            return "metax"
        if any(x in gpu_name for x in ["dcu", "海光", "hygon"]):
            return "hygon"
        return None
