import asyncio
import aiomysql
import os
import logging
import sys

# 设置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DBSetup")

async def setup_db():
    logger.info("🚀 Starting Cloud MySQL Table Setup...")
    
    # 优先采用环境变量，无则回退到默认隧道配置
    config = {
        "host": os.getenv("GSD_DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("GSD_DB_PORT", 36301)),
        "user": os.getenv("GSD_DB_USER", "root"),
        "password": os.getenv("GSD_DB_PASSWORD", "alwaysup@888"),
        "db": os.getenv("GSD_DB_NAME", "alwaysup"),
        "autocommit": True
    }
    
    logger.info(f"📍 Connecting to {config['host']}:{config['port']} (DB: {config['db']})")
    
    try:
        conn = await aiomysql.connect(**config)
        async with conn.cursor() as cur:
            # 创建精简版审计记录表
            logger.info("📝 Creating table `data_gate_audits`...")
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS `data_gate_audits` (
                `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                `trade_date` DATE NOT NULL COMMENT '交易日期',
                `gate_id` VARCHAR(20) NOT NULL COMMENT 'GATE_1/2/3',
                `is_complete` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '1: 完整, 0: 不完整',
                `description` VARCHAR(255) COMMENT '简要结果说明',
                `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE INDEX `idx_date_gate` (`trade_date`, `gate_id`)
            ) COMMENT='精简版数据门禁每日审计历史';
            """
            await cur.execute(create_table_sql)
            logger.info("✅ Table `data_gate_audits` created or already exists.")
            
        await conn.ensure_closed()
        logger.info("🎉 Database setup complete!")
    except Exception as e:
        logger.error(f"❌ Database setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(setup_db())
