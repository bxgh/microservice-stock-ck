from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class HardwareSpotPrice(BaseModel):
    """
    云端 GPU 现货/弹性实例价格模型
    """
    platform: str        # 平台名称 (e.g., 'autodl', 'aliyun')
    gpu_model: str       # GPU 型号 (e.g., 'RTX 4090', 'A100')
    instance_type: str   # 实例规格/机型名称
    price_per_hour: float # 每小时单价 (元)
    availability: float  # 可用度/库存状态 (0.0-1.0)
    collect_time: datetime # 采集时间

class HardwareProcurementTender(BaseModel):
    """
    政企招投标公告数据模型 (Story 18.2)
    """
    date: datetime      # 公告日期
    title: str         # 项目名称
    purchaser: str     # 采购单位
    winner: str        # 中标单位
    hardware_type: str # 核心硬件类型 (e.g., 'Ascend', 'NVIDIA', 'MetaX')
    amount: float      # 中标金额 (万元)
    region: str        # 地点/行政区划
    collect_time: datetime # 采集时间
