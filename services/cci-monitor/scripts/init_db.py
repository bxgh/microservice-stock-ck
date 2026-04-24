import asyncio
import sys
import os

# 将 src 目录加入路径
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.database import engine, Base
from src.core.logger import setup_logger
from src.db.models import CCIRecord, CCIAlert, CCIDislocation  # 确保模型被加载

async def init_db():
    logger = setup_logger()
    logger.info("Starting database initialization...")
    
    try:
        async with engine.begin() as conn:
            # 导出建表语句 (可选)
            # await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Database tables created successfully (CCI_ prefix used).")
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(init_db())
