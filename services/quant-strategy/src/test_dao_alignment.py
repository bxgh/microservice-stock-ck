import asyncio
import logging
import sys
import os

# 增加搜索路径
sys.path.append(os.path.join(os.getcwd(), "src"))

from dao.stock_info import StockInfoDAO

async def test_dao():
    logging.basicConfig(level=logging.INFO)
    dao = StockInfoDAO()
    
    code = "688802.SH"
    print(f"Testing DAO for {code}...")
    
    try:
        # 1. 测试基础信息
        meta_df = await dao.get_stock_meta([code])
        print("\nStock Meta:")
        print(meta_df)
        
        if not meta_df.empty:
            name = meta_df.iloc[0]['name']
            print(f"Name from DAO: {name}")
            if name == "沐曦股份":
                print("✅ Meta data ALIGNED!")
            else:
                print(f"❌ Meta data MISMATCH: {name}")
        else:
            print("❌ Meta data EMPTY")
            
        # 2. 测试发行价
        issue_df = await dao.get_issue_price([code])
        print("\nIssue Price:")
        print(issue_df)
        
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    asyncio.run(test_dao())
