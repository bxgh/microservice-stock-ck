#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuotesService 快速验证脚本

验证 QuotesService 基本功能是否正常工作。

Usage:
    python scripts/test_quotes_service.py
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data_services import QuotesService


async def main():
    """主测试函数"""
    print("=" * 60)
    print("QuotesService 快速验证")
    print("=" * 60)
    
    service = QuotesService()
    
    # 初始化
    print("\n1. 初始化服务...")
    success = await service.initialize()
    if not success:
        print("❌ 初始化失败")
        return
    print("✅ 初始化成功")
    
    try:
        # 测试1: 批量查询
        print("\n2. 测试批量查询 (get_quotes)...")
        codes = ['000001', '600519', '000858']
        df = await service.get_quotes(codes)
        print(f"✅ 成功获取 {len(df)} 只股票行情")
        print(f"   字段: {list(df.columns)[:10]}...")  # 显示前10个字段
        print(f"   示例数据:\n{df[['code', 'name', 'price', 'change_pct']].to_string()}")
        
        # 测试2: 单个查询
        print("\n3. 测试单个查询 (get_quote)...")
        quote = await service.get_quote('000001')
        if quote is not None:
            print(f"✅ {quote['name']} ({quote['code']})")
            print(f"   最新价: {quote['price']:.2f}  涨跌幅: {quote['change_pct']:.2f}%")
        
        # 测试3: 缓存命中
        print("\n4. 测试缓存命中...")
        df2 = await service.get_quotes(codes)  # 第二次查询，应该hit缓存
        stats = service.get_stats()
        print(f"✅ 统计信息:")
        print(f"   总请求: {stats['total_requests']}")
        print(f"   缓存命中率: {stats.get('cache_hit_rate', 'N/A')}")
        
        # 测试4: 涨停股票 (如果有）
        print("\n5. 测试涨停股票筛选...")
        try:
            limit_up = await service.get_limit_up_stocks()
            print(f"✅ 涨停股票数量: {len(limit_up)}")
            if not limit_up.empty:
                print(f"   示例: {limit_up[['code', 'name', 'change_pct']].head(3).to_string()}")
        except Exception as e:
            print(f"⚠️ 涨停筛选需要全市场数据: {e}")
        
        # 测试5: 字典格式
        print("\n6. 测试字典格式 (get_quotes_dict)...")
        quotes_dict = await service.get_quotes_dict(['000001'])
        if quotes_dict:
            code = list(quotes_dict.keys())[0]
            print(f"✅ 字典格式: {code} => {quotes_dict[code]}")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await service.close()
        print("\n服务已关闭")


if __name__ == "__main__":
    asyncio.run(main())
