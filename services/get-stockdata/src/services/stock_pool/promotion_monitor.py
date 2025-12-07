"""
Promotion Monitor

Background task that periodically scans the surge rankings (飙升榜) from RankingService
and promotes hot stocks to the dynamic pool for high-frequency data collection.

Features:
- Runs every 5 minutes during trading hours (09:35-15:00)
- Uses RankingService.get_surge_rank() as data source
- Promotes top N stocks from surge rankings
- Respects trading hour constraints
"""
import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Optional, TYPE_CHECKING
from zoneinfo import ZoneInfo

from .dynamic_pool_manager import DynamicPoolManager
from .anomaly_detector import AnomalyStock

if TYPE_CHECKING:
    from src.data_services.ranking_service import RankingService

logger = logging.getLogger(__name__)

# China timezone
CST = ZoneInfo("Asia/Shanghai")


class PromotionMonitor:
    """
    晋升监控器
    
    基于 RankingService 飙升榜定期扫描，将热门股票晋升到动态采集池。
    
    运行约束:
    - 仅在交易时段运行 (09:35-15:00)
    - 跳过集合竞价阶段 (09:30之前)
    - 每5分钟扫描一次
    """
    
    def __init__(
        self,
        dynamic_pool: DynamicPoolManager,
        ranking_service: "RankingService",
        scan_interval: int = 300,  # 5 minutes in seconds
        top_n: int = 20,  # Promote top N stocks from surge rank
        ttl_minutes: int = 30,  # How long promoted stocks stay in pool
    ):
        self.dynamic_pool = dynamic_pool
        self.ranking_service = ranking_service
        self.scan_interval = scan_interval
        self.top_n = top_n
        self.ttl_minutes = ttl_minutes
        
        # Task control
        self._task: Optional[asyncio.Task] = None
        self._running = False
        
        # Trading hours (only scan during these periods)
        self.trading_start = time(9, 35)  # Skip call auction
        self.trading_end = time(15, 0)
        
        # Statistics
        self.scans_performed = 0
        self.stocks_promoted = 0
        self.last_scan_at: Optional[datetime] = None
        
        logger.info(
            f"📊 PromotionMonitor initialized: "
            f"interval={scan_interval}s, top_n={top_n}, ttl={ttl_minutes}min"
        )
    
    async def start(self):
        """Start the background monitoring task."""
        if self._running:
            logger.warning("⚠️ PromotionMonitor is already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("✅ PromotionMonitor started")
    
    async def stop(self):
        """Stop the background monitoring task."""
        if not self._running:
            return
        
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.info("⏹️ PromotionMonitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        logger.info(f"🔄 PromotionMonitor loop started, interval={self.scan_interval}s")
        
        while self._running:
            try:
                # Check if within trading hours
                if self._is_trading_hours():
                    await self._scan_and_promote()
                else:
                    logger.debug("⏸️ Outside trading hours, skipping scan")
                
                # Wait for next scan
                await asyncio.sleep(self.scan_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in promotion monitor loop: {e}", exc_info=True)
                # Wait a bit before retrying to avoid tight error loops
                await asyncio.sleep(60)
    
    def _is_trading_hours(self) -> bool:
        """Check if current time is within trading hours."""
        now = datetime.now(CST).time()
        
        # Morning session: 09:35 - 11:30
        morning_start = time(9, 35)
        morning_end = time(11, 30)
        
        # Afternoon session: 13:00 - 15:00
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 0)
        
        is_morning = morning_start <= now <= morning_end
        is_afternoon = afternoon_start <= now <= afternoon_end
        
        return is_morning or is_afternoon
    
    async def _scan_and_promote(self):
        """Scan surge rankings and promote stocks."""
        try:
            # Fetch surge rank from RankingService
            logger.info("🔍 Scanning surge rankings...")
            surge_df = await self.ranking_service.get_surge_rank(limit=self.top_n)
            
            if surge_df is None or surge_df.empty:
                logger.warning("⚠️ No surge rank data available")
                return
            
            # Process surge rank data
            now = datetime.now(CST)
            expire_at = now + timedelta(minutes=self.ttl_minutes)
            promoted_count = 0
            
            for idx, row in surge_df.head(self.top_n).iterrows():
                # Extract stock info
                code = str(row.get('代码', row.get('code', '')))
                name = str(row.get('名称', row.get('name', '')))
                rank = idx + 1  # 1-based ranking
                
                if not code:
                    continue
                
                # Create AnomalyStock for promotion
                anomaly = AnomalyStock(
                    code=code,
                    name=name,
                    trigger_reason=f"飙升榜Top{rank}",
                    trigger_value=float(rank),  # Use rank as value
                    detected_at=now,
                    expire_at=expire_at,
                )
                
                # Promote to dynamic pool
                await self.dynamic_pool.promote(anomaly)
                promoted_count += 1
            
            # Update statistics
            self.scans_performed += 1
            self.stocks_promoted += promoted_count
            self.last_scan_at = now
            
            logger.info(
                f"✅ Promoted {promoted_count} stocks from surge rank "
                f"(total scans: {self.scans_performed}, total promoted: {self.stocks_promoted})"
            )
            
            # Cleanup expired stocks
            await self.dynamic_pool.cleanup_expired()
            
        except Exception as e:
            logger.error(f"❌ Failed to scan and promote: {e}", exc_info=True)
    
    async def force_scan(self):
        """Force an immediate scan (for API use)."""
        logger.info("🔄 Force scan triggered via API")
        await self._scan_and_promote()
    
    def get_stats(self) -> dict:
        """Get monitoring statistics."""
        return {
            "running": self._running,
            "scan_interval_seconds": self.scan_interval,
            "top_n": self.top_n,
            "ttl_minutes": self.ttl_minutes,
            "scans_performed": self.scans_performed,
            "stocks_promoted": self.stocks_promoted,
            "last_scan_at": self.last_scan_at.isoformat() if self.last_scan_at else None,
            "is_trading_hours": self._is_trading_hours(),
        }
