
import asyncio
import os
import sys
import logging
import akshare as ak
import redis.asyncio as redis
import pandas as pd
from typing import Dict

# Ensure src is in path
sys.path.insert(0, "/app")

from src.config.settings import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def sync_industries():
    logger.info("Starting Industry Sync Check...")
    
    # 1. Connect to Redis (Optional / Graceful)
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_password = os.getenv("REDIS_PASSWORD", "")
    redis_db = os.getenv("REDIS_DB", "0")

    if redis_password:
        redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    else:
        redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        
    r = redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
    redis_connected = False
    try:
        if await r.ping():
            logger.info("✅ Redis connected.")
            redis_connected = True
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed: {e}. Data will NOT be cached.")

    first_success = False

    # 2. Fetch all industries
    # Try generic API or Local Akshare
    try:
        logger.info("Fetching Industry List from Akshare...")
        if os.getenv("STOCK_API_URL"):
            # TODO: Implement remote call if needed
            pass
            
        df_ind = ak.stock_board_industry_name_em()
        if df_ind is not None and not df_ind.empty:
            logger.info(f"Found {len(df_ind)} industries via Akshare.")
            # Process ...
            # Reuse existing mapping logic for Akshare df structure
            # But wait, existing logic is inside this try block.
            first_success = True
            
            # ... loop ... (existing code structure requires refactoring to handle multiple sources cleanly)
            # For quick fix, let's keep Akshare logic here and wrap Baostock in except/else
            
            stock_industry_map = {} 
            for _, row in df_ind.iterrows():
                ind_name = row['板块名称']
                ind_code = row['板块代码']
                # ... fetch constituents ...
                try:
                    df_stocks = ak.stock_board_industry_cons_em(symbol=ind_code)
                    if df_stocks is not None and not df_stocks.empty:
                        for _, s_row in df_stocks.iterrows():
                            code = str(s_row['代码'])
                            stock_industry_map[code] = {"industry": ind_name, "industry_code": ind_code}
                except:
                    pass
            
    except Exception as e:
        logger.warning(f"Akshare fetch failed: {e}")

    # 3. Fallback to Baostock if Akshare failed or empty
    if not first_success or (locals().get('stock_industry_map') is None):
        logger.info("Attempting Fallback to Baostock...")
        try:
            import baostock as bs
            lg = bs.login()
            if lg.error_code != '0':
                logger.error(f"Baostock login failed: {lg.error_msg}")
            else:
                logger.info("Baostock login success.")
                rs = bs.query_stock_industry()
                
                # Baostock returns ResultSet, need to iterate
                data_list = []
                while (rs.error_code == '0') and rs.next():
                    data_list.append(rs.get_row_data())
                    
                if data_list:
                    # Columns: update_date, code, code_name, industry, industryClassification
                    # mapped to list
                    # Verify column order? rs.fields can tell us?
                    # default: date, code, code_name, industry, industryClassification
                    
                    stock_industry_map = {}
                    count = 0
                    for row in data_list:
                        # row is list of strings
                        # code is index 1?
                        # industry is index 3?
                        # Let's check fields
                        # fields = rs.fields -> "update_date,code,code_name,industry,industryClassification"
                        
                        code = row[1]
                        industry = row[3]
                        if industry and industry != "":
                            stock_industry_map[code] = {
                                "industry": industry,
                                "industry_code": row[4] # industryClassification (e.g. mfg)
                            }
                            count += 1
                    
                    logger.info(f"Mapped {len(stock_industry_map)} stocks via Baostock.")
                    first_success = True
                
                bs.logout()
                
        except ImportError:
            logger.error("Baostock not installed.")
        except Exception as e:
            logger.error(f"Baostock failed: {e}")

    if not first_success:
        logger.error("Failed to fetch data from ALL sources.")
        return

    logger.info(f"Total Stocks Mapped: {len(stock_industry_map)}")

    # 4. Save to Redis
    if redis_connected:
        pipe = r.pipeline()
        for code, info in stock_industry_map.items():
            key = f"stock:{code}:industry_info"
            import json
            pipe.set(key, json.dumps(info))
            
        await pipe.execute()
        logger.info("✅ Saved industry info to Redis.")
    else:
        logger.info("⚠️ Skipping Redis write (Not connected).")
    
    await r.close()

if __name__ == "__main__":
    asyncio.run(sync_industries())
