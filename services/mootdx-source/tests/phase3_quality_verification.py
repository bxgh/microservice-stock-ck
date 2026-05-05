#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mootdx Phase 3 数据质量验证工具
覆盖: 股票列表 (Stocks), 财务信息 (Finance), 除权除息 (XDXR), 指数K线 (IndexBars)
"""

import pandas as pd
from mootdx.quotes import Quotes
import sys

class Phase3Validator:
    def __init__(self):
        print("正在初始化 Phase 3 验证器...")
        self.client = Quotes.factory(market='std', bestip=True)
        print("✓ Mootdx client 准备就绪")

    def validate_stocks(self):
        """验证股票列表接口"""
        print(f"\n{'='*60}")
        print("验证股票列表 (get_stocks)")
        print(f"{'='*60}")
        
        try:
            # 获取上海和深圳市场数据
            sz_data = self.client.stocks(market=0)
            sh_data = self.client.stocks(market=1)
            
            total_count = len(sz_data) + len(sh_data)
            print(f"✓ 深圳市场: {len(sz_data)} 只")
            print(f"✓ 上海市场: {len(sh_data)} 只")
            print(f"✓ 总计: {total_count} 只")
            
            if total_count > 40000:
                print("✅ 数量符合预期 (包含股票、基金、债券等)")
            else:
                print(f"⚠️ 数量偏少: {total_count}")

            return total_count
        except Exception as e:
            print(f"❌ 股票列表验证失败: {e}")
            return 0

    def validate_finance(self, code):
        """验证财务信息接口"""
        print(f"\n{'='*60}")
        print(f"验证财务信息: {code}")
        print(f"{'='*60}")
        
        try:
            df = self.client.finance(symbol=code)
            if df is None or df.empty:
                print("❌ 未获取到财务数据")
                return None
            
            print(f"✓ 获取到财务字段: {list(df.columns)}")
            
            # 检查关键字段
            critical_fields = ['liutongguben', 'zongguben', 'industry', 'ipo_date']
            found = [f for f in critical_fields if f in df.columns]
            print(f"✅ 发现关键字段: {found}")
            
            return df
        except Exception as e:
            print(f"❌ 财务信息验证失败: {e}")
            return None

    def validate_xdxr(self, code):
        """验证除权除息接口"""
        print(f"\n{'='*60}")
        print(f"验证除权除息: {code}")
        print(f"{'='*60}")
        
        try:
            df = self.client.xdxr(symbol=code)
            if df is None or df.empty:
                print("❌ 未获取到除权除息数据")
                return None
            
            print(f"✓ 获取到 {len(df)} 条历史除权记录")
            last_record = df.iloc[-1]
            print(f"✅ 最近记录: {last_record.get('year')}-{last_record.get('month')}-{last_record.get('day')} (Category: {last_record.get('category')})")
            
            return df
        except Exception as e:
            print(f"❌ 除权除息验证失败: {e}")
            return None

    def validate_index_bars(self, code):
        """验证指数K线接口"""
        print(f"\n{'='*60}")
        print(f"验证指数K线: {code}")
        print(f"{'='*60}")
        
        try:
            # 频率 9 为日线
            df = self.client.index_bars(symbol=code, frequency=9, offset=100)
            if df is None or df.empty:
                print("❌ 未获取到指数K线数据")
                return None
            
            print(f"✓ 获取到 {len(df)} 条指数K线记录")
            # 校验指数特有字段
            if 'up_count' in df.columns and 'down_count' in df.columns:
                print("✅ 包含上涨/下跌家数统计字段")
            
            return df
        except Exception as e:
            print(f"❌ 指数K线验证失败: {e}")
            return None

def main():
    validator = Phase3Validator()
    
    # 1. 股票列表
    validator.validate_stocks()
    
    # 2. 财务信息 (茅台)
    validator.validate_finance("600519")
    
    # 3. 除权除息 (宁德时代)
    validator.validate_xdxr("300750")
    
    # 4. 指数K线 (上证指数)
    validator.validate_index_bars("000001")

if __name__ == "__main__":
    main()
