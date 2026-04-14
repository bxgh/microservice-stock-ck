import os
import tushare as ts
import pandas as pd
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(".env.tushare")

def test_tushare_connection():
    """
    测试 Tushare API 连通性并获取示例数据
    """
    token = os.getenv("TUSHARE_TOKEN")
    
    if not token or token == "your_tushare_token_here":
        print("❌ 错误: 未在 .env.tushare 中配置有效的 TUSHARE_TOKEN")
        return
    
    print(f"开始初始化 Tushare SDK (Token 长度: {len(token)})...")
    ts.set_token(token)
    pro = ts.pro_api()
    
    try:
        # 1. 测试获取股票列表 (基础信息)
        print("\n[1/2] 正在请求 A 股股票列表 (基础信息)...")
        data = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
        
        if not data.empty:
            print(f"✅ 成功! 获取到 {len(data)} 只股票信息。")
            print("数据样本 (前 5 行):")
            print(data.head())
        else:
            print("⚠️ 警告: 返回数据为空。")
            
        # 2. 测试获取单一股票日线行情
        print("\n[2/2] 正在请求 贵州茅台 (600519.SH) 最近 5 个交易日的行情...")
        df = pro.daily(ts_code='600519.SH', start_date='20260101', end_date='20260401')
        
        if not df.empty:
            print("✅ 成功! 日线数据样本:")
            print(df.head())
        else:
            print("⚠️ 警告: 未获取到 600519.SH 的行情数据。")
            
    except Exception as e:
        print(f"❌ 发生异常: {str(e)}")
        if "权限" in str(e) or "积分" in str(e):
            print("💡 提示: 可能是您的 Tushare 积分不足以调用该接口，请检查官网权限说明。")

if __name__ == "__main__":
    print("="*50)
    print("Tushare 数据采集环境调试脚本")
    print("="*50)
    test_tushare_connection()
    print("\n调试结束。")
