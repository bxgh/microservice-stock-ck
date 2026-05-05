#!/usr/bin/env python3
"""
验证脚本：检查 UniverseStock 表的数据
"""
import sys
sys.path.insert(0, '/home/bxgh/microservice-stock/services/quant-strategy/src')

import asyncio
from sqlalchemy import select, func
from database import init_database
from database.session import get_session
from database.stock_pool_models import UniverseStock

async def check_universe_pool():
    """检查 Universe Pool 状态"""
    # 初始化数据库
    await init_database()
    
    async for session in get_session():
        # 总数
        total_count = (await session.execute(
            select(func.count()).select_from(UniverseStock)
        )).scalar()
        
        print(f"📊 Universe Pool 统计")
        print(f"=" * 50)
        print(f"总记录数: {total_count}")
        
        if total_count == 0:
            print("❌ 表为空，数据同步可能尚未完成")
            return
        
        # 合格数量
        qualified_count = (await session.execute(
            select(func.count()).select_from(UniverseStock)
            .where(UniverseStock.is_qualified == True)
        )).scalar()
        
        print(f"合格股票数: {qualified_count}")
        print(f"不合格股票数: {total_count - qualified_count}")
        
        # 行业字段填充情况
        has_industry = (await session.execute(
            select(func.count()).select_from(UniverseStock)
            .where(UniverseStock.industry.isnot(None))
        )).scalar()
        
        print(f"\n📈 行业信息填充情况")
        print(f"有行业信息的股票: {has_industry} ({has_industry/total_count*100:.1f}%)")
        
        # 查看前10条记录
        result = await session.execute(
            select(UniverseStock).limit(10)
        )
        stocks = result.scalars().all()
        
        print(f"\n📋 前10条记录样本:")
        print(f"{'-' * 100}")
        for stock in stocks[:10]:
            print(f"代码: {stock.code:8s} | 名称: {stock.name:10s} | "
                  f"行业: {stock.industry or 'N/A':15s} | "
                  f"合格: {'✓' if stock.is_qualified else '✗'} | "
                  f"理由: {stock.disqualify_reason or 'N/A'}")
        
        # 行业分布
        if has_industry > 0:
            industry_result = await session.execute(
                select(
                    UniverseStock.industry,
                    func.count(UniverseStock.id).label('count')
                )
                .where(UniverseStock.industry.isnot(None))
                .group_by(UniverseStock.industry)
                .order_by(func.count(UniverseStock.id).desc())
                .limit(10)
            )
            
            print(f"\n🏭 TOP 10 行业分布:")
            print(f"{'-' * 50}")
            for row in industry_result:
                print(f"{row.industry:20s}: {row.count:4d} 只股票")
        
        print(f"\n✅ 验证完成")

if __name__ == "__main__":
    asyncio.run(check_universe_pool())
