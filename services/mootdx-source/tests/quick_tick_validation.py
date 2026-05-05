#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分笔数据质量快速验证脚本 (独立版本)
直接使用 mootdx 库，不依赖项目代码
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import Dict, Any, List, Optional
from mootdx.quotes import Quotes


class QuickTickValidator:
    """快速分笔数据验证器"""
    
    def __init__(self):
        self.client = Quotes.factory(market='std', bestip=True)
        print("✓ Mootdx client initialized")
    
    def validate_stock(self, code: str, date: str = None) -> Dict[str, Any]:
        """验证单个股票的分笔数据
        
        Args:
            code: 股票代码
            date: 交易日期 YYYYMMDD (可选，如 20241218)
        """
        print(f"\n{'='*60}")
        print(f"验证股票: {code} (日期: {date or '今日'})")
        print(f"{'='*60}")
        
        # 获取分笔数据
        try:
            if date:
                df = self.client.transactions(symbol=code, date=int(date))
            else:
                df = self.client.transactions(symbol=code)
        except Exception as e:
            print(f"❌ 获取分笔数据失败: {e}")
            return {"code": code, "status": "FAILED", "error": str(e)}
        
        if df is None or df.empty:
            print(f"⚠️ 无分笔数据")
            return {"code": code, "status": "NO_DATA"}
        
        print(f"✓ 获取到 {len(df)} 条分笔记录")
        
        results = {
            "code": code,
            "record_count": len(df),
            "columns": list(df.columns),
            "checks": {}
        }
        
        # 1. 字段检查
        print("\n[1] 字段检查:")
        print(f"  列名: {list(df.columns)}")
        print(f"  数据类型:\n{df.dtypes}")
        print(f"  前3条数据:\n{df.head(3)}")
        
        # 2. 价格检查
        print("\n[2] 价格检查:")
        if 'price' in df.columns:
            price_stats = {
                "min": float(df['price'].min()),
                "max": float(df['price'].max()),
                "mean": float(df['price'].mean()),
                "std": float(df['price'].std())
            }
            print(f"  最小价格: {price_stats['min']:.2f}")
            print(f"  最大价格: {price_stats['max']:.2f}")
            print(f"  平均价格: {price_stats['mean']:.2f}")
            print(f"  价格波动: {price_stats['std']:.2f}")
            
            # 检查异常价格
            negative_price = (df['price'] <= 0).sum()
            if negative_price > 0:
                print(f"  ⚠️ 发现 {negative_price} 条价格 <= 0")
            
            results['checks']['price'] = price_stats
        
        # 3. 成交量检查
        print("\n[3] 成交量检查:")
        if 'volume' in df.columns:
            vol_stats = {
                "total": int(df['volume'].sum()),
                "min": int(df['volume'].min()),
                "max": int(df['volume'].max()),
                "mean": float(df['volume'].mean())
            }
            print(f"  总成交量: {vol_stats['total']:,} 股")
            print(f"  单笔最小: {vol_stats['min']:,} 股")
            print(f"  单笔最大: {vol_stats['max']:,} 股")
            print(f"  单笔平均: {vol_stats['mean']:,.0f} 股")
            
            # 手数检查
            non_hundred = (df['volume'] % 100 != 0).sum()
            non_hundred_rate = non_hundred / len(df)
            print(f"  非100倍数: {non_hundred} 笔 ({non_hundred_rate:.1%})")
            
            # 异常大单
            large_orders = (df['volume'] > 1000000).sum()
            if large_orders > 0:
                print(f"  ⚠️ 发现 {large_orders} 笔超大单 (> 100万股)")
            
            results['checks']['volume'] = vol_stats
        
        # 4. 时间检查
        print("\n[4] 时间检查:")
        if 'time' in df.columns:
            print(f"  首笔时间: {df.iloc[0]['time']}")
            print(f"  末笔时间: {df.iloc[-1]['time']}")
            
            # 检查时间分布
            time_sample = df['time'].head(10).tolist()
            print(f"  时间样本: {time_sample}")
        
        # 5. 买卖方向检查
        print("\n[5] 买卖方向检查:")
        if 'type' in df.columns:
            type_dist = df['type'].value_counts().to_dict()
            print(f"  买卖分布: {type_dist}")
            results['checks']['direction'] = type_dist
        else:
            print(f"  ⚠️ 无 'type' 字段")
        
        # 6. 数据质量评分
        score = 1.0
        issues = []
        
        # 价格合理性
        if 'price' in df.columns:
            if (df['price'] <= 0).any():
                score -= 0.2
                issues.append("存在非正价格")
        
        # 成交量合理性
        if 'volume' in df.columns:
            if (df['volume'] < 0).any():
                score -= 0.2
                issues.append("存在负成交量")
            
            non_hundred_rate = (df['volume'] % 100 != 0).sum() / len(df)
            if non_hundred_rate > 0.10:
                score -= 0.1
                issues.append(f"过多非手数成交 ({non_hundred_rate:.1%})")
        
        results['quality_score'] = score
        results['issues'] = issues
        
        # 判定状态
        if score >= 0.9:
            status = "✅ EXCELLENT"
        elif score >= 0.7:
            status = "✅ GOOD"
        elif score >= 0.5:
            status = "⚠️ ACCEPTABLE"
        else:
            status = "❌ POOR"
        
        results['status'] = status
        
        print(f"\n{'='*60}")
        print(f"质量评分: {score:.2f} - {status}")
        if issues:
            print(f"发现问题:")
            for issue in issues:
                print(f"  - {issue}")
        print(f"{'='*60}")
        
        return results
    
    def validate_multiple_stocks(self, codes: List[str], date: str = None) -> List[Dict[str, Any]]:
        """批量验证多个股票
        
        Args:
            codes: 股票代码列表
            date: 交易日期 YYYYMMDD (可选)
        """
        results = []
        
        for i, code in enumerate(codes, 1):
            print(f"\n\n{'#'*70}")
            print(f"# [{i}/{len(codes)}] 测试股票: {code}")
            print(f"{'#'*70}")
            
            result = self.validate_stock(code, date=date)
            results.append(result)
        
        # 汇总报告
        print(f"\n\n{'='*70}")
        print(f"汇总报告")
        print(f"{'='*70}")
        
        total = len(results)
        successful = sum(1 for r in results if r.get('status', '').startswith('✅'))
        
        print(f"测试股票数: {total}")
        print(f"通过数量: {successful}")
        print(f"通过率: {successful/total:.1%}")
        
        avg_score = sum(r.get('quality_score', 0) for r in results if 'quality_score' in r) / total
        print(f"平均评分: {avg_score:.2f}")
        
        print(f"\n详细结果:")
        print(f"{'-'*70}")
        for r in results:
            code = r['code']
            status = r.get('status', 'UNKNOWN')
            score = r.get('quality_score', 0)
            count = r.get('record_count', 0)
            print(f"{code:10s} | {status:20s} | Score: {score:.2f} | Records: {count:,}")
        
        print(f"{'='*70}\n")
        
        return results


def main():
    """主函数"""
    
    # 测试股票列表
    test_stocks = [
        "000001",  # 平安银行
        "600519",  # 贵州茅台
        "600000",  # 浦发银行
        "000858",  # 五粮液
        "300750",  # 宁德时代
    ]
    
    # 使用最近的交易日 (2024年12月18日 周三)
    test_date = "20241218"
    
    print("="*70)
    print("分笔数据质量快速验证工具")
    print("="*70)
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试日期: {test_date}")
    print(f"测试股票: {len(test_stocks)} 只")
    print("="*70)
    
    validator = QuickTickValidator()
    results = validator.validate_multiple_stocks(test_stocks, date=test_date)
    
    print("\n✓ 验证完成!")


if __name__ == "__main__":
    main()
