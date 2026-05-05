import asyncio
import logging
import argparse
import aiomysql
import docker
import json
import os
from pathlib import Path
from datetime import datetime

# 确保能导入 src 目录下的模块
import sys
sys.path.append(str(Path(__file__).parent))

from config.settings import settings
from config.task_loader import TaskLoader
from core.command_poller import CommandPoller

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("shard_poller")

async def main():
    parser = argparse.ArgumentParser(description="Distributed Shard Command Poller")
    parser.add_argument("--shard", type=int, required=True, help="Shard ID to handle")
    parser.add_argument("--interval", type=int, default=15, help="Poll interval in seconds")
    args = parser.parse_args()

    logger.info(f"🚀 Starting Shard Poller for Shard {args.shard}...")

    # 1. Initialize MySQL Connection Pool
    try:
        mysql_pool = await aiomysql.create_pool(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            db=settings.MYSQL_DATABASE,
            minsize=1,
            maxsize=5,
            pool_recycle=3600,
            autocommit=True
        )
        logger.info(f"✓ Connected to MySQL: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}")
    except Exception as e:
        logger.error(f"❌ MySQL Connection failed: {e}")
        return

    # 2. Initialize Docker Client
    try:
        docker_client = docker.DockerClient(base_url=settings.DOCKER_HOST)
        logger.info(f"🐳 Connected to Docker: {settings.DOCKER_HOST}")
    except Exception as e:
        logger.error(f"❌ Docker connection failed: {e}")
        return

    # 3. Load Task Config (required for workflow execution)
    try:
        config_path = Path(__file__).parent.parent / "config" / "tasks.yml"
        loader = TaskLoader()
        task_config = loader.load_from_yaml(str(config_path))
        logger.info(f"✓ Loaded tasks configuration")
    except Exception as e:
        logger.error(f"❌ Failed to load tasks.yml: {e}")
        return

    # 4. Start Command Poller
    # Note: Shard pollers don't run scheduled jobs, so scheduler=None
    poller = CommandPoller(
        mysql_pool=mysql_pool,
        scheduler=None, 
        docker_client=docker_client,
        task_config=task_config,
        poll_interval=args.interval,
        shard_id=args.shard
    )

    await poller.start()
    logger.info(f"📡 Poller is active. Shard ID: {args.shard}")
    
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Stopping...")
        await poller.stop()
        mysql_pool.close()
        await mysql_pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
