
"""
SignalDispatcher 信号分发器

监听 AnalysisService 的事件并驱动策略生成信号。
"""
import json
import logging
from typing import Any

import pandas as pd

from cache.redis_client import redis_client
from core.event_bus import EventBus
from strategies.registry import StrategyRegistry

logger = logging.getLogger(__name__)

class SignalDispatcher:
    """
    信号协调器

    订阅 "market_analysis_completed" 主题。
    当分析完成时，调用 LeadLagStrategy 生成信号，并分发至输出渠道。
    """

    def __init__(self, registry: StrategyRegistry | None = None):
        self.bus = EventBus()
        self.registry = registry or StrategyRegistry()
        self.output_topic = "quant:signals:lead_lag"

    async def initialize(self):
        """初始化并订阅事件"""
        self.bus.subscribe("market_analysis_completed", self.on_market_analysis_completed)
        logger.info("📡 SignalDispatcher initialized and subscribed to market_analysis_completed")

    async def on_market_analysis_completed(self, event_data: dict[str, Any]):
        """
        分析完成回调
        """
        trade_date = event_data.get("trade_date")
        report = event_data.get("report", [])

        # 获取 LeadLagStrategy 实例
        strategy = self.registry.get("strat_lead_lag_001")

        if not strategy:
            logger.error("❌ LeadLagStrategy not found in registry. Skipping signal generation.")
            return

        # 生成信号
        signals = await strategy.generate_signals_from_analysis(trade_date, pd.DataFrame(report))

        if not signals:
            return

        # 分发信号 (Push to Redis)
        await self._dispatch_signals(signals)

    async def _dispatch_signals(self, signals: list):
        """
        将信号推送到 Redis 队列
        """
        client = await redis_client.get_client()

        pipeline = client.pipeline()
        for sig in signals:
            sig_dict = sig.to_dict()
            # 推送到实时队列
            pipeline.lpush(self.output_topic, json.dumps(sig_dict))
            # 同时发布 Pub/Sub 消息用于实时监控
            pipeline.publish(f"{self.output_topic}:pub", json.dumps(sig_dict))

        try:
            await pipeline.execute()
            logger.info(f"🚀 Dispatched {len(signals)} signals to Redis {self.output_topic}")
        except Exception as e:
            logger.error(f"Failed to dispatch signals to Redis: {e}")

    async def close(self):
        """释放资源"""
        self.bus.unsubscribe("market_analysis_completed", self.on_market_analysis_completed)
        logger.info("SignalDispatcher closed")
