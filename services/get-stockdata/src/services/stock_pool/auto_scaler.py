"""
Auto-Scaler for Stock Pool

Automatically adjusts stock pool size based on system health metrics.
Implements US-004.04: 智能扩容系统

Scaling Path: 100 → 150 → 200 → 300 → 500 → 800

Scaling Conditions (all must be met):
- QPS < 0.8 (low load)
- Success Rate > 99% (stable)  
- CPU < 60% (resources available)
"""
import asyncio
import logging
import psutil
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from core.stock_pool.manager import StockPoolManager

logger = logging.getLogger(__name__)

CST = ZoneInfo("Asia/Shanghai")


class ScaleDirection(Enum):
    UP = "up"
    DOWN = "down"
    NONE = "none"


@dataclass
class ScaleDecision:
    """扩容决策结果"""
    should_scale: bool
    direction: ScaleDirection
    reason: str
    current_tier: int
    target_tier: int
    current_size: int
    target_size: int
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class ScalingMetrics:
    """系统健康指标"""
    qps: float = 0.0
    success_rate: float = 1.0
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(CST))


class AutoScaler:
    """
    智能扩容管理器
    
    根据系统健康指标自动调整股票池大小。
    支持手动和自动两种模式。
    
    Attributes:
        SCALING_PATH: 扩容路径 [100, 150, 200, 300, 500, 800]
        current_tier: 当前扩容层级 (0-5)
        auto_mode: 是否启用自动扩容
    """
    
    # 扩容路径
    SCALING_PATH: List[int] = [100, 150, 200, 300, 500, 800]
    
    # 扩容条件阈值
    SCALE_UP_THRESHOLDS = {
        "qps_max": 0.8,           # QPS < 0.8 (系统负载低)
        "success_rate_min": 0.99, # 成功率 > 99%
        "cpu_max": 60.0,          # CPU < 60%
    }
    
    # 缩容条件阈值 (可选)
    SCALE_DOWN_THRESHOLDS = {
        "qps_min": 2.0,           # QPS > 2.0 (系统超载)
        "success_rate_max": 0.95, # 成功率 < 95%
        "cpu_min": 80.0,          # CPU > 80%
    }
    
    # 冷却时间
    COOLDOWN_PERIOD = timedelta(minutes=30)
    
    # 连续满足次数才触发
    CONSECUTIVE_CHECKS_REQUIRED = 3
    
    def __init__(
        self,
        stock_pool_manager: Optional["StockPoolManager"] = None,
        check_interval: int = 300,  # 5分钟
        auto_mode: bool = False,    # 默认关闭自动模式
    ):
        self.stock_pool_manager = stock_pool_manager
        self.check_interval = check_interval
        self.auto_mode = auto_mode
        
        # 当前层级 (默认 tier 0 = 100 only)
        self._current_tier = 0
        
        # 冷却控制
        self._last_scale_time: Optional[datetime] = None
        
        # 连续满足计数
        self._consecutive_up_count = 0
        self._consecutive_down_count = 0
        
        # 运行状态
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # 历史记录
        self._scale_history: List[Dict[str, Any]] = []
        
        # 指标缓存
        self._last_metrics: Optional[ScalingMetrics] = None
        
        # 锁
        self._lock = asyncio.Lock()
        
        logger.info(f"AutoScaler initialized: tier={self._current_tier}, "
                    f"size={self.get_current_capacity()}, auto_mode={auto_mode}")
    
    @property
    def current_tier(self) -> int:
        return self._current_tier
    
    def get_current_capacity(self) -> int:
        """获取当前股票池容量"""
        if 0 <= self._current_tier < len(self.SCALING_PATH):
            return self.SCALING_PATH[self._current_tier]
        return self.SCALING_PATH[0]
    
    def get_tier_for_size(self, size: int) -> int:
        """根据大小获取对应的层级"""
        for i, path_size in enumerate(self.SCALING_PATH):
            if size <= path_size:
                return i
        return len(self.SCALING_PATH) - 1
    
    async def get_metrics(self) -> ScalingMetrics:
        """
        获取当前系统指标
        
        Returns:
            ScalingMetrics: 当前指标快照
        """
        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        
        # QPS 和成功率 - 从 Prometheus 指标获取
        # 简化实现: 从本地统计获取
        qps = 0.0
        success_rate = 1.0
        
        try:
            # 尝试从 Prometheus 客户端获取
            from prometheus_client import REGISTRY
            
            # 获取请求计数
            for metric in REGISTRY.collect():
                if metric.name == 'stockdata_requests_total':
                    total = 0
                    success = 0
                    for sample in metric.samples:
                        if sample.name == 'stockdata_requests_total':
                            total += sample.value
                            if sample.labels.get('status') == 'success':
                                success += sample.value
                    
                    if total > 0:
                        success_rate = success / total
                        # QPS 近似 (基于总请求数和运行时间)
                        # 这里简化为固定值，实际应该用 rate 计算
                        qps = 0.5  # 默认低负载
                    break
        except Exception as e:
            logger.debug(f"Could not get Prometheus metrics: {e}")
        
        metrics = ScalingMetrics(
            qps=qps,
            success_rate=success_rate,
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            timestamp=datetime.now(CST)
        )
        
        self._last_metrics = metrics
        return metrics
    
    def _is_in_cooldown(self) -> bool:
        """检查是否在冷却期内"""
        if self._last_scale_time is None:
            return False
        
        elapsed = datetime.now(CST) - self._last_scale_time
        return elapsed < self.COOLDOWN_PERIOD
    
    async def check_scale_conditions(self) -> ScaleDecision:
        """
        检查是否满足扩容/缩容条件
        
        Returns:
            ScaleDecision: 扩容决策
        """
        metrics = await self.get_metrics()
        
        current_size = self.get_current_capacity()
        
        # 检查冷却期
        if self._is_in_cooldown():
            return ScaleDecision(
                should_scale=False,
                direction=ScaleDirection.NONE,
                reason="在冷却期内",
                current_tier=self._current_tier,
                target_tier=self._current_tier,
                current_size=current_size,
                target_size=current_size,
                metrics=self._metrics_to_dict(metrics)
            )
        
        # 检查扩容条件
        can_scale_up = (
            self._current_tier < len(self.SCALING_PATH) - 1 and
            metrics.qps < self.SCALE_UP_THRESHOLDS["qps_max"] and
            metrics.success_rate > self.SCALE_UP_THRESHOLDS["success_rate_min"] and
            metrics.cpu_percent < self.SCALE_UP_THRESHOLDS["cpu_max"]
        )
        
        # 检查缩容条件
        can_scale_down = (
            self._current_tier > 0 and
            (metrics.qps > self.SCALE_DOWN_THRESHOLDS["qps_min"] or
             metrics.success_rate < self.SCALE_DOWN_THRESHOLDS["success_rate_max"] or
             metrics.cpu_percent > self.SCALE_DOWN_THRESHOLDS["cpu_min"])
        )
        
        # 更新连续计数
        if can_scale_up:
            self._consecutive_up_count += 1
            self._consecutive_down_count = 0
        elif can_scale_down:
            self._consecutive_down_count += 1
            self._consecutive_up_count = 0
        else:
            self._consecutive_up_count = 0
            self._consecutive_down_count = 0
        
        # 判断是否触发
        if self._consecutive_up_count >= self.CONSECUTIVE_CHECKS_REQUIRED:
            target_tier = self._current_tier + 1
            return ScaleDecision(
                should_scale=True,
                direction=ScaleDirection.UP,
                reason=f"连续 {self._consecutive_up_count} 次满足扩容条件",
                current_tier=self._current_tier,
                target_tier=target_tier,
                current_size=current_size,
                target_size=self.SCALING_PATH[target_tier],
                metrics=self._metrics_to_dict(metrics)
            )
        
        if self._consecutive_down_count >= self.CONSECUTIVE_CHECKS_REQUIRED:
            target_tier = self._current_tier - 1
            return ScaleDecision(
                should_scale=True,
                direction=ScaleDirection.DOWN,
                reason=f"连续 {self._consecutive_down_count} 次满足缩容条件",
                current_tier=self._current_tier,
                target_tier=target_tier,
                current_size=current_size,
                target_size=self.SCALING_PATH[target_tier],
                metrics=self._metrics_to_dict(metrics)
            )
        
        return ScaleDecision(
            should_scale=False,
            direction=ScaleDirection.NONE,
            reason=f"扩容计数: {self._consecutive_up_count}/{self.CONSECUTIVE_CHECKS_REQUIRED}, "
                   f"缩容计数: {self._consecutive_down_count}/{self.CONSECUTIVE_CHECKS_REQUIRED}",
            current_tier=self._current_tier,
            target_tier=self._current_tier,
            current_size=current_size,
            target_size=current_size,
            metrics=self._metrics_to_dict(metrics)
        )
    
    async def scale_up(self, force: bool = False) -> bool:
        """
        执行扩容
        
        Args:
            force: 是否强制扩容（忽略冷却期和条件检查）
            
        Returns:
            bool: 是否成功
        """
        async with self._lock:
            if self._current_tier >= len(self.SCALING_PATH) - 1:
                logger.warning("已达最大容量，无法继续扩容")
                return False
            
            if not force and self._is_in_cooldown():
                logger.warning("在冷却期内，无法扩容")
                return False
            
            old_tier = self._current_tier
            old_size = self.get_current_capacity()
            
            self._current_tier += 1
            new_size = self.get_current_capacity()
            
            # 更新 StockPoolManager
            if self.stock_pool_manager:
                self.stock_pool_manager.max_pool_size = new_size
            
            # 记录冷却时间
            self._last_scale_time = datetime.now(CST)
            
            # 重置计数
            self._consecutive_up_count = 0
            
            # 记录历史
            self._scale_history.append({
                "timestamp": datetime.now(CST).isoformat(),
                "direction": "up",
                "from_tier": old_tier,
                "to_tier": self._current_tier,
                "from_size": old_size,
                "to_size": new_size,
                "forced": force
            })
            
            logger.info(f"📈 扩容成功: {old_size} → {new_size} (tier {old_tier} → {self._current_tier})")
            return True
    
    async def scale_down(self, force: bool = False) -> bool:
        """
        执行缩容
        
        Args:
            force: 是否强制缩容
            
        Returns:
            bool: 是否成功
        """
        async with self._lock:
            if self._current_tier <= 0:
                logger.warning("已达最小容量，无法继续缩容")
                return False
            
            if not force and self._is_in_cooldown():
                logger.warning("在冷却期内，无法缩容")
                return False
            
            old_tier = self._current_tier
            old_size = self.get_current_capacity()
            
            self._current_tier -= 1
            new_size = self.get_current_capacity()
            
            # 更新 StockPoolManager
            if self.stock_pool_manager:
                self.stock_pool_manager.max_pool_size = new_size
            
            # 记录冷却时间
            self._last_scale_time = datetime.now(CST)
            
            # 重置计数
            self._consecutive_down_count = 0
            
            # 记录历史
            self._scale_history.append({
                "timestamp": datetime.now(CST).isoformat(),
                "direction": "down",
                "from_tier": old_tier,
                "to_tier": self._current_tier,
                "from_size": old_size,
                "to_size": new_size,
                "forced": force
            })
            
            logger.info(f"📉 缩容成功: {old_size} → {new_size} (tier {old_tier} → {self._current_tier})")
            return True
    
    async def set_tier(self, tier: int) -> bool:
        """
        手动设置层级
        
        Args:
            tier: 目标层级 (0 到 len(SCALING_PATH)-1)
            
        Returns:
            bool: 是否成功
        """
        if tier < 0 or tier >= len(self.SCALING_PATH):
            logger.error(f"无效的层级: {tier}")
            return False
        
        async with self._lock:
            old_tier = self._current_tier
            old_size = self.get_current_capacity()
            
            self._current_tier = tier
            new_size = self.get_current_capacity()
            
            # 更新 StockPoolManager
            if self.stock_pool_manager:
                self.stock_pool_manager.max_pool_size = new_size
            
            # 记录冷却时间
            self._last_scale_time = datetime.now(CST)
            
            # 重置计数
            self._consecutive_up_count = 0
            self._consecutive_down_count = 0
            
            logger.info(f"🎯 手动设置层级: {old_size} → {new_size} (tier {old_tier} → {tier})")
            return True
    
    def set_auto_mode(self, enabled: bool):
        """开关自动扩容模式"""
        self.auto_mode = enabled
        logger.info(f"自动扩容模式: {'开启' if enabled else '关闭'}")
    
    async def run_check_loop(self):
        """运行自动检查循环"""
        self._running = True
        logger.info(f"AutoScaler 检查循环启动，间隔: {self.check_interval}秒")
        
        while self._running:
            try:
                if self.auto_mode:
                    decision = await self.check_scale_conditions()
                    
                    if decision.should_scale:
                        if decision.direction == ScaleDirection.UP:
                            await self.scale_up()
                        elif decision.direction == ScaleDirection.DOWN:
                            await self.scale_down()
                
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"AutoScaler 检查异常: {e}")
                await asyncio.sleep(60)  # 错误后等待 1 分钟
        
        logger.info("AutoScaler 检查循环已停止")
    
    def start(self):
        """启动自动检查"""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run_check_loop())
            logger.info("AutoScaler 已启动")
    
    def stop(self):
        """停止自动检查"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("AutoScaler 已停止")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取扩容器状态"""
        return {
            "current_tier": self._current_tier,
            "current_size": self.get_current_capacity(),
            "max_tier": len(self.SCALING_PATH) - 1,
            "scaling_path": self.SCALING_PATH,
            "auto_mode": self.auto_mode,
            "running": self._running,
            "in_cooldown": self._is_in_cooldown(),
            "cooldown_remaining": self._get_cooldown_remaining(),
            "consecutive_up_count": self._consecutive_up_count,
            "consecutive_down_count": self._consecutive_down_count,
            "last_metrics": self._metrics_to_dict(self._last_metrics) if self._last_metrics else None,
            "scale_history": self._scale_history[-10:],  # 最近 10 条
            "thresholds": {
                "scale_up": self.SCALE_UP_THRESHOLDS,
                "scale_down": self.SCALE_DOWN_THRESHOLDS,
            }
        }
    
    def _get_cooldown_remaining(self) -> Optional[str]:
        """获取冷却剩余时间"""
        if not self._is_in_cooldown():
            return None
        
        elapsed = datetime.now(CST) - self._last_scale_time
        remaining = self.COOLDOWN_PERIOD - elapsed
        return str(remaining).split('.')[0]  # 去掉微秒
    
    @staticmethod
    def _metrics_to_dict(metrics: Optional[ScalingMetrics]) -> Dict[str, Any]:
        """转换指标为字典"""
        if not metrics:
            return {}
        return {
            "qps": round(metrics.qps, 3),
            "success_rate": round(metrics.success_rate, 4),
            "cpu_percent": round(metrics.cpu_percent, 1),
            "memory_percent": round(metrics.memory_percent, 1),
            "timestamp": metrics.timestamp.isoformat()
        }
