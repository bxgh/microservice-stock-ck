#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mootdx Phase 2 数据质量验证工具
覆盖: 实时行情 (Quotes) 和 历史K线 (History)
"""

import pandas as pd
import numpy as np
from mootdx.quotes import Quotes
from datetime import datetime
import json

class Phase2Validator:
    def __init__(self):
        print("正在初始化 Phase 2 验证器...")
        self.client = Quotes.factory(market='std', bestip=True)
        print("✓ Mootdx client 准备就绪")

    def validate_quotes(self, codes):
        """验证实时行情数据质量"""
        print(f"\n{'='*60}")
        print(f"验证实时行情: {codes}")
        print(f"{'='*60}")
        
        try:
            df = self.client.quotes(symbol=codes)
            if df is None or df.empty:
                print("❌ 未获取到行情数据")
                return None
            
            print(f"✓ 获取到 {len(df)} 条行情记录")
            
            # 1. 字段完整性检查
            required_fields = ['open', 'high', 'low', 'price', 'bid1', 'ask1', 'vol', 'amount']
            missing = [f for f in required_fields if f not in df.columns]
            if missing:
                print(f"⚠️ 缺失核心字段: {missing}")
            else:
                print("✅ 核心字段完整 (OHLC, Bid/Ask, Vol, Amount)")

            # 2. 价格逻辑检查
            results = []
            for _, row in df.iterrows():
                code = row.get('code', 'Unknown')
                errors = []
                
                # OHLC 逻辑
                if not (row['low'] <= row['open'] <= row['high']): errors.append("Open out of LH range")
                if not (row['low'] <= row['price'] <= row['high']): errors.append("Price out of LH range")
                if not (row['low'] <= row['high']): errors.append("Low > High")
                
                # 买卖盘逻辑
                if 'bid1' in row and 'ask1' in row:
                    if row['bid1'] >= row['ask1'] and row['bid1'] > 0 and row['ask1'] > 0:
                        errors.append(f"Bid1({row['bid1']}) >= Ask1({row['ask1']})")

                # 成交量逻辑
                if row['vol'] < 0: errors.append("Negative Volume")

                status = "✅ PASS" if not errors else f"❌ FAIL ({'; '.join(errors)})"
                print(f"[{code}] {status}")
                results.append({"code": code, "status": status, "errors": errors})

            return results
        except Exception as e:
            print(f"❌ 行情验证执行失败: {e}")
            return None

    def validate_history(self, code, frequency='d', offset=800):
        """验证历史K线数据质量"""
        print(f"\n{'='*60}")
        print(f"验证历史K线: {code} (频率: {frequency}, 长度: {offset})")
        print(f"{'='*60}")
        
        freq_map = {"d": 9, "w": 6, "m": 5}
        mootdx_freq = freq_map.get(frequency, 9)
        
        try:
            df = self.client.bars(symbol=code, frequency=mootdx_freq, offset=offset)
            if df is None or df.empty:
                print("❌ 未获取到历史K线数据")
                return None
            
            print(f"✓ 获取到 {len(df)} 条K线记录")
            
            # 1. 数据连续性检查 (简单日期排序检查)
            if 'datetime' in df.columns:
                df['dt'] = pd.to_datetime(df['datetime'])
                is_sorted = df['dt'].is_monotonic_increasing
                print(f"时间单调性: {'✅ 正确' if is_sorted else '❌ 错误'}")
            
            # 2. 逻辑一致性校验
            logic_errors = 0
            for i, row in df.iterrows():
                if not (row['low'] <= row['open'] <= row['high'] and row['low'] <= row['close'] <= row['high']):
                    logic_errors += 1
            
            if logic_errors == 0:
                print("✅ OHLC 内部逻辑校验 100% 通过")
            else:
                print(f"❌ 发现 {logic_errors} 条 K 线存在 OHLC 逻辑错误")

            # 3. 边界测试
            print(f"数据量验证: 请求 {offset}, 实际返回 {len(df)} {'(Limit Hit)' if len(df) == 800 else ''}")
            
            return {"code": code, "records": len(df), "logic_errors": logic_errors}
        except Exception as e:
            print(f"❌ 历史K线验证执行失败: {e}")
            return None

def main():
    validator = Phase2Validator()
    
    # 测试代码
    test_codes = ["000001", "600519", "000858", "300750", "600000"]
    
    # 1. 实时行情验证
    validator.validate_quotes(test_codes)
    
    # 2. 历史K线验证
    for code in test_codes[:2]: # 测试前两个
        validator.validate_history(code, frequency='d', offset=800)
        validator.validate_history(code, frequency='w', offset=100)

if __name__ == "__main__":
    main()
