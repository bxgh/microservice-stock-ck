"""
验证 MySQL DAO 直连功能
"""
import asyncio
import logging
import os
import sys
import pandas as pd
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# 强制设置环境参数匹配 41 隧道路由
os.environ["GSD_DB_HOST"] = "127.0.0.1"
os.environ["GSD_DB_PORT"] = "36301"

from data_access import (
    MySQLPoolManager,
    StockBasicDAO,
    ValuationDAO,
    MarketDataDAO,
    SectorDAO,
    FinanceDAO
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify-daos")

async def verify():
    logger.info("开始审计 MySQL DAO 只读连通性...")
    
    try:
        pool = await MySQLPoolManager.get_pool()
        
        # 1. 验证 StockBasicDAO
        basic_dao = StockBasicDAO()
        stocks = await basic_dao.get_all_stocks(pool)
        if not stocks.empty:
            logger.info(f"✓ StockBasicDAO: 成功获取股票列表, 样本量: {len(stocks)}")
            # 测试个股检索
            test_code = stocks.iloc[0]['symbol']
            info = await basic_dao.get_stock_info(pool, test_code)
            if info:
                logger.info(f"  - 个股检索测试 ({test_code}): {info.get('name')} OK")
        else:
            logger.warning("! StockBasicDAO: 股票列表为空，请检查库表同步情况")

        # 2. 验证 ValuationDAO
        valuation_dao = ValuationDAO()
        if not stocks.empty:
            test_code = stocks.iloc[0]['symbol']
            val = await valuation_dao.get_latest_valuation(pool, test_code)
            if val:
                logger.info(f"✓ ValuationDAO: 成功获取 {test_code} 最新估值, PE={val.get('pe')}")
            else:
                logger.warning(f"! ValuationDAO: 未找到 {test_code} 的估值记录")

        # 3. 验证 MarketDataDAO
        market_dao = MarketDataDAO()
        if not stocks.empty:
            test_code = stocks.iloc[0]['symbol']
            lhb = await market_dao.get_lhb_data(pool, test_code)
            logger.info(f"✓ MarketDataDAO: LHB 数据检索成功, 记录数: {len(lhb)}")

        # 4. 验证 SectorDAO
        sector_dao = SectorDAO()
        sectors = await sector_dao.get_all_sectors(pool)
        if not sectors.empty:
            logger.info(f"✓ SectorDAO: 成功获取板块列表, 样本量: {len(sectors)}")
            test_sector_id = sectors.iloc[0]['id']
            test_sector_name = sectors.iloc[0]['name']
            members = await sector_dao.get_sector_members(pool, test_sector_id)
            logger.info(f"  - 板块成分检索测试 ({test_sector_name}): 成员数={len(members)}")
        else:
            logger.warning("! SectorDAO: 板块列表为空")

        # 5. 验证 FinanceDAO (全面验证聚合视图)
        finance_dao = FinanceDAO()
        if not stocks.empty:
            test_code = stocks.iloc[0]['symbol']
            fina = await finance_dao.get_latest_indicators(pool, test_code)
            if fina:
                logger.info(f"✓ FinanceDAO: 成功获取 {test_code} 聚合财务指标")
                logger.info(f"  - 业务字段映射校验: report_date={fina.get('report_date')}, total_revenue={fina.get('total_revenue')}")
                logger.info(f"  - 跨表关联校验: total_assets={fina.get('total_assets')} (来自资产负债表), net_cash_flow_total={fina.get('net_cash_flow_total')} (来自现金流量表)")
                
                if 'total_assets' in fina and 'total_revenue' in fina:
                    logger.info("✓ FinanceDAO: 三表 JOIN 关联完整性验证通过")
                else:
                    logger.warning("! FinanceDAO (聚合): 部分报表数据缺失，请检查库表关联完整性")
            else:
                logger.warning(f"! FinanceDAO (聚合): 未能获取 {test_code} 的财务数据，请确认表是否存在且包含数据")
                
            # 验证新加的 derivative indicators
            derived = await finance_dao.get_derived_indicators(pool, test_code)
            if derived:
                logger.info(f"✓ FinanceDAO (衍生指标): 成功读取独立存在的衍生指标 - ROE={derived.get('roe')}, 资产负债率={derived.get('asset_liab_ratio')}")
            else:
                logger.warning(f"! FinanceDAO (衍生指标): 未提取到标的 {test_code} 的 stock_finance_indicators 数据。")

    except Exception as e:
        logger.error(f"审计过程中发生崩溃: {e}")
    finally:
        await MySQLPoolManager.close_pool()
        logger.info("审计结束。")

if __name__ == "__main__":
    asyncio.run(verify())
