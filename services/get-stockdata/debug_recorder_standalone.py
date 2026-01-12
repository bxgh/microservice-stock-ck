import os
import sys
import asyncio
import logging
from datetime import datetime

# Set up PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
sys.path.insert(0, src_dir)

# Mocking environment variables
os.environ['STOCK_POOL_CONFIG'] = os.path.join(current_dir, 'config/hs300_stocks.yaml')
os.environ['CLICKHOUSE_HOST'] = '127.0.0.1'
os.environ['CLICKHOUSE_PORT'] = '9000'
os.environ['CLICKHOUSE_USER'] = 'default'
os.environ['CLICKHOUSE_PASSWORD'] = ''
os.environ['HTTP_PROXY'] = 'http://192.168.151.18:3128'
os.environ['HTTPS_PROXY'] = 'http://192.168.151.18:3128'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DebugRecorder")

from src.core.recorder.snapshot_recorder import SnapshotRecorder

async def run_debug():
    logger.info("🚀 Starting Debug Snapshot Recorder...")
    
    recorder = SnapshotRecorder()
    
    # Check if we can load the stock pool
    stocks = recorder.pool_manager.get_pool_symbols()
    logger.info(f"Stock pool size: {len(stocks)}")
    if not stocks:
        logger.error("❌ Stock pool is empty! Check config path.")
        return

    # Create the task for recorder.start()
    recorder_task = asyncio.create_task(recorder.start())
    
    logger.info("✅ Recorder task started. Running for 30 seconds...")
    
    try:
        # Run for 30 seconds to capture a few rounds
        await asyncio.sleep(30)
        
    except Exception as e:
        logger.error(f"❌ Error during debug run: {e}", exc_info=True)
    finally:
        logger.info("🛑 Signalling recorder to stop...")
        recorder.stop() # This is NOT async
        
        # Give it a few seconds to finish the current round and clean up
        try:
            await asyncio.wait_for(recorder_task, timeout=10)
        except asyncio.TimeoutError:
            logger.warning("⚠️ Recorder task did not stop in time, cancelling...")
            recorder_task.cancel()
            
        logger.info("🏁 Debug run finished")

if __name__ == "__main__":
    asyncio.run(run_debug())
