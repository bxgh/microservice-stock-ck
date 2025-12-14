"""
财务指标数据模型

用于基本面分析和风险过滤
"""

from pydantic import BaseModel, Field


class FinancialIndicators(BaseModel):
    """财务指标数据模型"""
    
    stock_code: str = Field(..., description="股票代码")
    report_date: str = Field(..., description="报告期 (YYYY-MM-DD)")
    
    # 资产负债表指标
    goodwill: float = Field(..., description="商誉 (亿元)")
    net_assets: float = Field(..., description="净资产 (亿元)")
    monetary_funds: float = Field(..., description="货币资金 (亿元)")
    total_assets: float = Field(..., description="总资产 (亿元)")
    interest_bearing_debt: float = Field(..., description="有息负债 (亿元)")
    
    # 现金流量表指标
    operating_cash_flow: float = Field(..., description="经营性现金流净额 (亿元)")
    
    # 利润表指标
    net_profit: float = Field(..., description="净利润 (亿元)")
    
    # 股权结构指标
    major_shareholder_pledge_ratio: float = Field(..., description="大股东质押率 (0-1)")
    
    @property
    def goodwill_ratio(self) -> float:
        """商誉占净资产比例"""
        if self.net_assets <= 0:
            return 0.0
        return self.goodwill / self.net_assets
    
    @property
    def cash_to_profit_ratio(self) -> float:
        """收现比 (经营现金流/净利润)"""
        if self.net_profit <= 0:
            return 0.0
        return self.operating_cash_flow / self.net_profit
    
    @property
    def cash_ratio(self) -> float:
        """货币资金占总资产比例"""
        if self.total_assets <= 0:
            return 0.0
        return self.monetary_funds / self.total_assets
    
    @property
    def debt_ratio(self) -> float:
        """有息负债占总资产比例"""
        if self.total_assets <= 0:
            return 0.0
        return self.interest_bearing_debt / self.total_assets
    
    class Config:
        """Pydantic配置"""
        json_schema_extra = {
            "example": {
                "stock_code": "600519",
                "report_date": "2024-09-30",
                "goodwill": 5.2,
                "net_assets": 150.0,
                "monetary_funds": 30.0,
                "total_assets": 300.0,
                "interest_bearing_debt": 20.0,
                "operating_cash_flow": 15.0,
                "net_profit": 12.0,
                "major_shareholder_pledge_ratio": 0.15
            }
        }
