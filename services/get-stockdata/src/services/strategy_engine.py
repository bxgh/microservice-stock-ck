#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态策略切换引擎
支持运行时调整数据源优先级和策略
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class StrategyType(Enum):
    """策略类型枚举"""
    SPEED_FIRST = "speed_first"        # 速度优先
    COST_FIRST = "cost_first"          # 成本优先
    RELIABILITY_FIRST = "reliability_first"  # 可靠性优先
    ACCURACY_FIRST = "accuracy_first"  # 精度优先
    BALANCED = "balanced"              # 平衡策略
    CUSTOM = "custom"                  # 自定义策略

class DataSourceMetrics:
    """数据源指标跟踪"""

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.request_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.total_response_time = 0.0
        self.last_success_time = None
        self.last_failure_time = None
        self.consecutive_failures = 0
        self.availability_score = 100.0
        self.performance_score = 100.0
        self.cost_score = 100.0

    def record_success(self, response_time: float):
        """记录成功请求"""
        self.request_count += 1
        self.success_count += 1
        self.total_response_time += response_time
        self.last_success_time = datetime.now()
        self.consecutive_failures = 0

        # 更新性能分数
        avg_response_time = self.total_response_time / self.success_count
        if avg_response_time < 0.5:
            self.performance_score = 100
        elif avg_response_time < 1.0:
            self.performance_score = 80
        elif avg_response_time < 2.0:
            self.performance_score = 60
        else:
            self.performance_score = 40

        # 更新可用性分数
        self._update_availability_score()

    def record_failure(self, error_type: str = "unknown"):
        """记录失败请求"""
        self.request_count += 1
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        self.consecutive_failures += 1

        # 更新可用性分数
        self._update_availability_score()

    def _update_availability_score(self):
        """更新可用性分数"""
        if self.request_count == 0:
            self.availability_score = 100.0
            return

        success_rate = self.success_count / self.request_count

        # 基于成功率计算可用性分数
        if success_rate >= 0.95:
            self.availability_score = 100
        elif success_rate >= 0.90:
            self.availability_score = 90
        elif success_rate >= 0.80:
            self.availability_score = 75
        elif success_rate >= 0.70:
            self.availability_score = 60
        elif success_rate >= 0.50:
            self.availability_score = 40
        else:
            self.availability_score = 20

        # 连续失败惩罚
        if self.consecutive_failures >= 5:
            self.availability_score = max(0, self.availability_score - 50)
        elif self.consecutive_failures >= 3:
            self.availability_score = max(0, self.availability_score - 20)

    def get_composite_score(self, strategy_weights: Dict[str, float]) -> float:
        """根据策略权重计算综合分数"""
        score = 0.0

        if "performance" in strategy_weights:
            score += self.performance_score * strategy_weights["performance"]

        if "availability" in strategy_weights:
            score += self.availability_score * strategy_weights["availability"]

        if "cost" in strategy_weights:
            score += self.cost_score * strategy_weights["cost"]

        return score

class StrategyEngine:
    """动态策略切换引擎"""

    def __init__(self):
        # 数据源指标跟踪
        self.source_metrics: Dict[str, DataSourceMetrics] = {}

        # 策略配置
        self.strategies = self._init_strategies()

        # 当前活跃策略
        self.current_strategies: Dict[str, StrategyType] = {}

        # 数据源能力配置
        self.source_capabilities = self._init_source_capabilities()

        # 动态调整参数
        self.auto_adjustment_enabled = True
        self.adjustment_threshold = 10  # 调整阈值
        self.adjustment_interval = 300  # 调整间隔（秒）
        self.last_adjustment_time = datetime.now()

        # 熔断恢复机制
        self.circuit_breakers: Dict[str, Dict] = {}
        self.recovery_timeout = 60  # 恢复超时时间

        # 启动后台任务
        asyncio.create_task(self._background_monitoring_task())

    def _init_strategies(self) -> Dict[str, Dict]:
        """初始化策略配置"""
        return {
            StrategyType.SPEED_FIRST.value: {
                "name": "速度优先",
                "description": "优先选择响应最快的数据源",
                "weights": {
                    "performance": 0.6,
                    "availability": 0.3,
                    "cost": 0.1
                },
                "adjustment_rules": {
                    "response_time_threshold": 2.0,
                    "success_rate_threshold": 0.8
                }
            },
            StrategyType.COST_FIRST.value: {
                "name": "成本优先",
                "description": "优先选择免费数据源",
                "weights": {
                    "cost": 0.6,
                    "performance": 0.25,
                    "availability": 0.15
                },
                "adjustment_rules": {
                    "cost_increase_penalty": 0.8,
                    "free_source_bonus": 0.2
                }
            },
            StrategyType.RELIABILITY_FIRST.value: {
                "name": "可靠性优先",
                "description": "优先选择最稳定的数据源",
                "weights": {
                    "availability": 0.6,
                    "performance": 0.25,
                    "cost": 0.15
                },
                "adjustment_rules": {
                    "consecutive_failure_penalty": 0.9,
                    "downtime_penalty": 0.8
                }
            },
            StrategyType.ACCURACY_FIRST.value: {
                "name": "精度优先",
                "description": "优先选择数据质量最高的数据源",
                "weights": {
                    "accuracy": 0.5,
                    "availability": 0.3,
                    "performance": 0.15,
                    "cost": 0.05
                },
                "adjustment_rules": {
                    "data_validation_bonus": 0.2,
                    "consistency_bonus": 0.15
                }
            },
            StrategyType.BALANCED.value: {
                "name": "平衡策略",
                "description": "综合考虑各项指标",
                "weights": {
                    "performance": 0.25,
                    "availability": 25,
                    "cost": 0.25,
                    "accuracy": 0.25
                },
                "adjustment_rules": {
                    "balanced_adjustment": 0.1
                }
            }
        }

    def _init_source_capabilities(self) -> Dict[str, Dict]:
        """初始化数据源能力配置"""
        return {
            "akshare": {
                "cost_score": 100,  # 免费
                "accuracy_score": 85,
                "supported_data_types": ["realtime", "historical", "tick", "financial"],
                "markets": ["A股", "港股", "美股"],
                "base_priority": 1
            },
            "yfinance": {
                "cost_score": 100,  # 免费
                "accuracy_score": 90,
                "supported_data_types": ["realtime", "historical", "financial"],
                "markets": ["美股", "港股", "A股"],
                "base_priority": 2
            },
            "tushare": {
                "cost_score": 60,   # 付费
                "accuracy_score": 95,
                "supported_data_types": ["realtime", "historical", "financial", "sector"],
                "markets": ["A股", "港股"],
                "base_priority": 3
            },
            "alpha_vantage": {
                "cost_score": 40,   # 付费
                "accuracy_score": 92,
                "supported_data_types": ["realtime", "historical", "technical", "financial"],
                "markets": ["美股"],
                "base_priority": 4
            },
            "mootdx": {
                "cost_score": 100,  # 免费
                "accuracy_score": 82,
                "supported_data_types": ["realtime", "tick", "historical"],
                "markets": ["A股", "港股", "美股"],
                "base_priority": 2
            },
            "baostock": {
                "cost_score": 100,  # 免费
                "accuracy_score": 78,
                "supported_data_types": ["historical", "financial"],
                "markets": ["A股"],
                "base_priority": 5
            },
            "pandas": {
                "cost_score": 90,   # 基本免费
                "accuracy_score": 70,
                "supported_data_types": ["historical", "financial", "macro"],
                "markets": ["美股", "全球"],
                "base_priority": 6
            }
        }

    async def get_optimal_sources(
        self,
        data_type: str,
        market: str,
        strategy: Optional[StrategyType] = None,
        custom_weights: Optional[Dict[str, float]] = None
    ) -> List[Tuple[str, float]]:
        """
        获取最优数据源列表

        Args:
            data_type: 数据类型
            market: 市场类型
            strategy: 策略类型
            custom_weights: 自定义权重

        Returns:
            排序后的数据源列表 (source_name, score)
        """
        # 确定策略
        if strategy is None:
            strategy = self.current_strategies.get(data_type, StrategyType.BALANCED)

        # 获取策略权重
        if custom_weights:
            weights = custom_weights
        else:
            weights = self.strategies.get(strategy.value, {}).get("weights", {})

        # 筛选支持该数据类型和市场的数据源
        candidate_sources = []
        for source, capabilities in self.source_capabilities.items():
            if (data_type in capabilities.get("supported_data_types", []) and
                market in capabilities.get("markets", [])):
                candidate_sources.append(source)

        # 检查熔断器状态
        available_sources = []
        for source in candidate_sources:
            if not self._is_circuit_breaker_open(source):
                available_sources.append(source)

        # 计算每个数据源的综合分数
        source_scores = []
        for source in available_sources:
            if source not in self.source_metrics:
                self.source_metrics[source] = DataSourceMetrics(source)

            metrics = self.source_metrics[source]
            capabilities = self.source_capabilities[source]

            # 计算综合分数
            composite_score = metrics.get_composite_score(weights)

            # 添加基础优先级调整
            base_priority = capabilities.get("base_priority", 10)
            priority_adjustment = (10 - base_priority) * 5

            final_score = composite_score + priority_adjustment
            source_scores.append((source, final_score))

        # 按分数排序
        source_scores.sort(key=lambda x: x[1], reverse=True)

        return source_scores

    def _is_circuit_breaker_open(self, source: str) -> bool:
        """检查熔断器是否开启"""
        if source not in self.circuit_breakers:
            return False

        breaker = self.circuit_breakers[source]
        if breaker["state"] == "open":
            # 检查是否可以尝试恢复
            if datetime.now() - breaker["last_failure_time"] > timedelta(seconds=self.recovery_timeout):
                breaker["state"] = "half_open"
                breaker["attempt_count"] = 0
                logger.info(f"数据源 {source} 熔断器进入半开状态")
                return False
            else:
                return True

        return False

    def record_source_result(self, source: str, success: bool, response_time: float = 0.0, error: str = ""):
        """记录数据源调用结果"""
        if source not in self.source_metrics:
            self.source_metrics[source] = DataSourceMetrics(source)

        metrics = self.source_metrics[source]

        if success:
            metrics.record_success(response_time)
            # 成功后关闭熔断器
            if source in self.circuit_breakers:
                self.circuit_breakers[source]["state"] = "closed"
                self.circuit_breakers[source]["failure_count"] = 0
        else:
            metrics.record_failure(error)
            # 失败后可能开启熔断器
            self._handle_circuit_breaker(source, metrics)

    def _handle_circuit_breaker(self, source: str, metrics: DataSourceMetrics):
        """处理熔断器逻辑"""
        if source not in self.circuit_breakers:
            self.circuit_breakers[source] = {
                "state": "closed",
                "failure_count": 0,
                "last_failure_time": None,
                "attempt_count": 0
            }

        breaker = self.circuit_breakers[source]
        breaker["failure_count"] += 1
        breaker["last_failure_time"] = datetime.now()

        # 连续失败达到阈值时开启熔断器
        if metrics.consecutive_failures >= 3 or breaker["failure_count"] >= 5:
            breaker["state"] = "open"
            logger.warning(f"数据源 {source} 熔断器开启，连续失败 {metrics.consecutive_failures} 次")

    def set_strategy(self, data_type: str, strategy: StrategyType):
        """设置指定数据类型的策略"""
        self.current_strategies[data_type] = strategy
        logger.info(f"数据类型 {data_type} 策略更新为 {strategy.value}")

    def get_strategy_performance(self, data_type: str, strategy: StrategyType, time_window: int = 3600) -> Dict[str, Any]:
        """获取策略性能统计"""
        end_time = datetime.now()
        start_time = end_time - timedelta(seconds=time_window)

        total_requests = 0
        total_successes = 0
        total_failures = 0
        total_response_time = 0.0

        source_performance = {}

        for source, metrics in self.source_metrics.items():
            # 计算时间窗口内的统计
            window_requests = 0
            window_successes = 0
            window_failures = 0
            window_response_time = 0.0

            # 这里简化实现，实际应该基于时间窗口过滤
            source_performance[source] = {
                "total_requests": metrics.request_count,
                "success_count": metrics.success_count,
                "failure_count": metrics.failure_count,
                "success_rate": metrics.success_count / max(1, metrics.request_count),
                "avg_response_time": metrics.total_response_time / max(1, metrics.success_count),
                "availability_score": metrics.availability_score,
                "performance_score": metrics.performance_score
            }

            total_requests += metrics.request_count
            total_successes += metrics.success_count
            total_failures += metrics.failure_count
            total_response_time += metrics.total_response_time

        overall_stats = {
            "data_type": data_type,
            "strategy": strategy.value,
            "time_window": time_window,
            "total_requests": total_requests,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "overall_success_rate": total_successes / max(1, total_requests),
            "avg_response_time": total_response_time / max(1, total_successes),
            "source_performance": source_performance,
            "circuit_breakers": self.circuit_breakers
        }

        return overall_stats

    async def _background_monitoring_task(self):
        """后台监控任务"""
        while True:
            try:
                await asyncio.sleep(self.adjustment_interval)

                if self.auto_adjustment_enabled:
                    await self._auto_adjust_strategies()

                await self._cleanup_old_metrics()

            except Exception as e:
                logger.error(f"后台监控任务异常: {e}")
                await asyncio.sleep(60)  # 出错时等待1分钟再重试

    async def _auto_adjust_strategies(self):
        """自动调整策略"""
        try:
            current_time = datetime.now()

            # 检查是否需要调整
            if current_time - self.last_adjustment_time < timedelta(seconds=self.adjustment_interval):
                return

            for data_type in self.current_strategies:
                strategy = self.current_strategies[data_type]
                strategy_config = self.strategies.get(strategy.value, {})
                adjustment_rules = strategy_config.get("adjustment_rules", {})

                # 检查是否需要调整该数据类型的策略
                if await self._should_adjust_strategy(data_type, adjustment_rules):
                    new_strategy = await self._determine_optimal_strategy(data_type)
                    if new_strategy != strategy:
                        self.set_strategy(data_type, new_strategy)
                        logger.info(f"自动调整 {data_type} 策略: {strategy.value} -> {new_strategy.value}")

            self.last_adjustment_time = current_time

        except Exception as e:
            logger.error(f"自动调整策略异常: {e}")

    async def _should_adjust_strategy(self, data_type: str, rules: Dict[str, Any]) -> bool:
        """判断是否应该调整策略"""
        # 获取当前策略的性能统计
        current_strategy = self.current_strategies.get(data_type)
        if not current_strategy:
            return True

        performance = self.get_strategy_performance(data_type, current_strategy)

        # 根据调整规则判断
        if "response_time_threshold" in rules:
            avg_response_time = performance["avg_response_time"]
            if avg_response_time > rules["response_time_threshold"]:
                return True

        if "success_rate_threshold" in rules:
            success_rate = performance["overall_success_rate"]
            if success_rate < rules["success_rate_threshold"]:
                return True

        return False

    async def _determine_optimal_strategy(self, data_type: str) -> StrategyType:
        """确定最优策略"""
        # 评估各个策略的潜在性能
        strategy_scores = {}

        for strategy in StrategyType:
            if strategy == StrategyType.CUSTOM:
                continue  # 跳过自定义策略

            # 模拟使用该策略的性能
            test_sources = await self.get_optimal_sources(data_type, "A股", strategy)
            if test_sources:
                # 基于测试结果评估策略性能
                avg_score = sum(score for _, score in test_sources[:3]) / min(3, len(test_sources))
                strategy_scores[strategy] = avg_score

        # 选择得分最高的策略
        if strategy_scores:
            optimal_strategy = max(strategy_scores.items(), key=lambda x: x[1])[0]
            return optimal_strategy

        return StrategyType.BALANCED

    async def _cleanup_old_metrics(self):
        """清理旧的指标数据"""
        cutoff_time = datetime.now() - timedelta(hours=24)

        for source, metrics in list(self.source_metrics.items()):
            if metrics.last_success_time and metrics.last_success_time < cutoff_time:
                if metrics.request_count < 10:  # 如果请求次数很少，保留更长时间
                    continue

                logger.info(f"清理数据源 {source} 的旧指标数据")
                del self.source_metrics[source]

                # 同时清理熔断器状态
                if source in self.circuit_breakers:
                    del self.circuit_breakers[source]

    def get_real_time_status(self) -> Dict[str, Any]:
        """获取实时状态信息"""
        return {
            "active_strategies": {k: v.value for k, v in self.current_strategies.items()},
            "source_metrics": {
                source: {
                    "requests": m.request_count,
                    "successes": m.success_count,
                    "failures": m.failure_count,
                    "success_rate": m.success_count / max(1, m.request_count),
                    "avg_response_time": m.total_response_time / max(1, m.success_count),
                    "availability_score": m.availability_score,
                    "consecutive_failures": m.consecutive_failures,
                    "last_success": m.last_success_time.isoformat() if m.last_success_time else None,
                    "last_failure": m.last_failure_time.isoformat() if m.last_failure_time else None
                }
                for source, m in self.source_metrics.items()
            },
            "circuit_breakers": self.circuit_breakers,
            "auto_adjustment_enabled": self.auto_adjustment_enabled,
            "last_adjustment": self.last_adjustment_time.isoformat(),
            "monitoring_interval": self.adjustment_interval
        }