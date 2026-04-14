import asyncio
import aiomysql
from config.settings import settings

async def create_table():
    print(f"Connecting to {settings.db_host}:{settings.db_port}/{settings.db_name}...")
    conn = await aiomysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        db=settings.db_name,
        charset='utf8mb4',
        autocommit=True
    )
    
    async with conn.cursor() as cursor:
        # 1. 创建流动性指标表
        ddl_table = """
        CREATE TABLE IF NOT EXISTS market_review_liquidity (
            trade_date DATE PRIMARY KEY COMMENT '交易日期',
            vol_ma_divergence DECIMAL(10,4) COMMENT 'VOL-01 成交额均线背离(动能差)',
            vol_rank DECIMAL(10,4) COMMENT 'VOL-01 当日成交额历史百分位',
            vol_ma5_rank DECIMAL(10,4) COMMENT 'VOL-01 MA5成交额历史百分位',
            vol_ma20_rank DECIMAL(10,4) COMMENT 'VOL-01 MA20成交额历史百分位',
            vol_01_state VARCHAR(32) COMMENT 'VOL-01 动能状态机名称',
            margin_ratio DECIMAL(10,4) COMMENT 'VOL-02 融资买入占成交额比例',
            margin_velocity DECIMAL(10,4) COMMENT 'VOL-02 融资买入动量的占比加速度',
            vol_02_state VARCHAR(32) COMMENT 'VOL-02 杠杆动能状态机名称',
            congestion_velocity DECIMAL(10,4) COMMENT 'VOL-03 极值拥挤度的加速度(前10%虹吸比)',
            zombie_stock_derivation DECIMAL(10,4) COMMENT 'VOL-04 极寒无流动性股衍生率(Z-Score)',
            cost_pulse_fdr007 DECIMAL(10,4) COMMENT 'VOL-05 资金成本的异常脉冲(FR007)',
            non_bank_premium DECIMAL(10,4) COMMENT 'VOL-05 辅助非银流动性溢价(R007-FR007)',
            etf_depletion_rate DECIMAL(10,4) COMMENT 'VOL-06 ETF被动护盘的效用消耗斜率',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='全市场微观与宏观流动性二阶趋势表';
        """

        print("Executing DDL for market_review_liquidity...")
        await cursor.execute(ddl_table)
        
        # 2. 创建/刷新 每日复盘 综合视图
        # 注意：这里假设市场复盘的其他表（如 huijin, institution 等）已经存在，
        # 如果不存在，LEFT JOIN 仍然有效，只是该列为 NULL。
        ddl_view = """
        CREATE OR REPLACE VIEW view_market_daily_review AS
        SELECT 
            s.trade_date,
            l.vol_ma_divergence, 
            l.margin_velocity, 
            l.congestion_velocity, 
            l.zombie_stock_derivation, 
            l.cost_pulse_fdr007, 
            l.non_bank_premium, 
            l.etf_depletion_rate,
            l.updated_at AS liquidity_updated_at
        FROM (SELECT DISTINCT trade_date FROM market_review_liquidity) s
        LEFT JOIN market_review_liquidity l ON s.trade_date = l.trade_date;
        """
        # 备注：实际生产中 s 表应该是总表，这里先以 liquidity 表作为驱动
        print("Executing DDL for view_market_daily_review...")
        await cursor.execute(ddl_view)
        
    conn.close()
    print("DDL Execution Finished.")

if __name__ == "__main__":
    asyncio.run(create_table())
