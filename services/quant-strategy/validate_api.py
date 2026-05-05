"""
验证 get-stockdata API 数据可用性

测试当前 get-stockdata 服务能否提供 EPIC-002 所需的数据
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Any
from datetime import datetime


class GetStockDataAPIValidator:
    """get-stockdata API 验证器"""
    
    def __init__(self, base_url: str = "http://get-stockdata:8001"):
        self.base_url = base_url.rstrip('/')
        self.test_stock_code = "600519"  # 贵州茅台作为测试股票
        
    async def test_endpoint(self, endpoint: str, method: str = "GET") -> Dict[str, Any]:
        """测试单个 API 端点"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "status": "✅ 可用",
                            "http_code": 200,
                            "data": data
                        }
                    else:
                        return {
                            "status": f"⚠️ HTTP {resp.status}",
                            "http_code": resp.status,
                            "data": None
                        }
        except aiohttp.ClientConnectorError:
            return {
                "status": "❌ 连接失败 (服务未启动?)",
                "http_code": None,
                "data": None
            }
        except asyncio.TimeoutError:
            return {
                "status": "❌ 超时",
                "http_code": None,
                "data": None
            }
        except Exception as e:
            return {
                "status": f"❌ 错误: {str(e)}",
                "http_code": None,
                "data": None
            }
    
    def check_fields(self, data: Any, required_fields: List[str]) -> Dict[str, str]:
        """检查数据中是否包含必需字段"""
        if not data:
            return {field: "❌ 无数据" for field in required_fields}
        
        # 处理不同的数据结构
        if isinstance(data, dict):
            if 'data' in data:
                data = data['data']
            
            # 如果是列表，取第一个元素
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
        
        results = {}
        for field in required_fields:
            if isinstance(data, dict) and field in data:
                value = data[field]
                if value is not None and value != "":
                    results[field] = f"✅ {value}"
                else:
                    results[field] = "⚠️ 空值"
            else:
                results[field] = "❌ 缺失"
        
        return results
    
    async def validate_all_apis(self):
        """验证所有 API"""
        print("=" * 80)
        print("EPIC-002 数据需求验证报告")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试服务: {self.base_url}")
        print(f"测试股票: {self.test_stock_code}")
        print("=" * 80)
        print()
        
        # API 1: 财务指标接口
        print("【API 1】财务指标接口")
        print("-" * 80)
        result = await self.test_endpoint(f"/api/v1/finance/indicators/{self.test_stock_code}")
        print(f"端点: /api/v1/finance/indicators/{{stock_code}}")
        print(f"状态: {result['status']}")
        
        if result['data']:
            # Story 2.1 需要的字段
            story_21_fields = [
                "goodwill", "net_assets", "monetary_funds", 
                "interest_bearing_debt", "operating_cash_flow", 
                "net_profit", "major_shareholder_pledge_ratio"
            ]
            
            # Story 2.2 新增需要的字段
            story_22_fields = [
                "revenue", "operating_cost", "operating_profit",
                "accounts_receivable", "inventory", "accounts_payable",
                "total_assets"
            ]
            
            print("\nStory 2.1 所需字段:")
            field_results = self.check_fields(result['data'], story_21_fields)
            for field, status in field_results.items():
                print(f"  {field:35s}: {status}")
            
            print("\nStory 2.2 新增字段:")
            field_results = self.check_fields(result['data'], story_22_fields)
            for field, status in field_results.items():
                print(f"  {field:35s}: {status}")
        print()
        
        # API 2: 历史财务数据接口
        print("【API 2】历史财务数据接口")
        print("-" * 80)
        result = await self.test_endpoint(f"/api/v1/finance/history/{self.test_stock_code}")
        print(f"端点: /api/v1/finance/history/{{stock_code}}")
        print(f"状态: {result['status']}")
        if result['data']:
            print(f"数据示例: {json.dumps(result['data'], ensure_ascii=False, indent=2)[:200]}...")
        print()
        
        # API 3: 市场估值数据接口
        print("【API 3】市场估值数据接口")
        print("-" * 80)
        result = await self.test_endpoint(f"/api/v1/market/valuation/{self.test_stock_code}")
        print(f"端点: /api/v1/market/valuation/{{stock_code}}")
        print(f"状态: {result['status']}")
        
        if result['data']:
            valuation_fields = [
                "market_cap", "circulating_market_cap", "pe_ratio", 
                "pb_ratio", "ps_ratio", "dividend_yield",
                "total_shares", "circulating_shares"
            ]
            print("\nStory 2.3 所需字段:")
            field_results = self.check_fields(result['data'], valuation_fields)
            for field, status in field_results.items():
                print(f"  {field:35s}: {status}")
        print()
        
        # API 4: 估值历史数据接口
        print("【API 4】估值历史数据接口")
        print("-" * 80)
        result = await self.test_endpoint(f"/api/v1/market/valuation/{self.test_stock_code}/history")
        print(f"端点: /api/v1/market/valuation/{{stock_code}}/history")
        print(f"状态: {result['status']}")
        print()
        
        # API 5: 行业统计数据接口
        print("【API 5】行业统计数据接口")
        print("-" * 80)
        result = await self.test_endpoint("/api/v1/finance/industry/C39/stats")
        print(f"端点: /api/v1/finance/industry/{{industry_code}}/stats")
        print(f"状态: {result['status']}")
        print()
        
        # API 6: 股票基本信息接口
        print("【API 6】股票基本信息接口")
        print("-" * 80)
        result = await self.test_endpoint(f"/api/v1/stocks/{self.test_stock_code}/info")
        print(f"端点: /api/v1/stocks/{{stock_code}}/info")
        print(f"状态: {result['status']}")
        
        if result['data']:
            info_fields = [
                "stock_code", "name", "industry_code", 
                "industry_name", "listing_date"
            ]
            print("\n基本信息字段:")
            field_results = self.check_fields(result['data'], info_fields)
            for field, status in field_results.items():
                print(f"  {field:35s}: {status}")
        print()
        
        # 测试现有的实时行情接口
        print("【补充】实时行情接口 (已有)")
        print("-" * 80)
        result = await self.test_endpoint(f"/api/v1/datasources/test/{self.test_stock_code}")
        print(f"端点: /api/v1/datasources/test/{{stock_code}}")
        print(f"状态: {result['status']}")
        
        if result['data']:
            quote_fields = ["price", "volume", "name"]
            print("\n行情字段:")
            field_results = self.check_fields(result['data'], quote_fields)
            for field, status in field_results.items():
                print(f"  {field:35s}: {status}")
        print()
        
        # 总结
        print("=" * 80)
        print("验证总结")
        print("=" * 80)
        print("✅ = 字段可用且有数据")
        print("⚠️ = 端点可用但字段缺失/空值")
        print("❌ = 端点不存在或字段缺失")
        print()
        print("建议:")
        print("1. 优先实现缺失的财务指标字段 (revenue, operating_cost 等)")
        print("2. 新建历史财务数据接口 (API 2)")
        print("3. 新建市场估值相关接口 (API 3, 4)")
        print("4. 新建行业统计接口 (API 5)")
        print("=" * 80)


async def main():
    """主函数"""
    # 可以通过环境变量或参数指定 get-stockdata 服务地址
    import os
    base_url = os.getenv("STOCKDATA_URL", "http://get-stockdata:8001")
    
    validator = GetStockDataAPIValidator(base_url)
    await validator.validate_all_apis()


if __name__ == "__main__":
    asyncio.run(main())
