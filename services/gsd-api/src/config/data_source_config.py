#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源配置管理器
支持动态配置数据源优先级和策略
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import json
import os
from datetime import datetime

class DataCategory(Enum):
    """数据分类"""
    MARKET_DATA = "market_data"        # 市场数据
    PRICE_DATA = "price_data"          # 价格数据
    VOLUME_DATA = "volume_data"        # 成交量数据
    COMPANY_DATA = "company_data"      # 公司数据
    FINANCIAL_DATA = "financial_data"  # 财务数据
    TECHNICAL_DATA = "technical_data"  # 技术指标数据

class DataSourceStrategy(Enum):
    """数据源策略"""
    SPEED_FIRST = "speed_first"        # 速度优先
    COST_FIRST = "cost_first"          # 成本优先
    RELIABILITY_FIRST = "reliability_first"  # 可靠性优先
    ACCURACY_FIRST = "accuracy_first"  # 精度优先
    BALANCED = "balanced"              # 平衡策略

class DataSourceConfig:
    """数据源配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config/data_source_config.json"
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "strategies": {
                DataCategory.MARKET_DATA.value: {
                    "default_strategy": DataSourceStrategy.SPEED_FIRST.value,
                    "priorities": {
                        "A股": ["akshare", "tushare", "mootdx"],
                        "港股": ["akshare", "mootdx", "tushare"],
                        "美股": ["yfinance", "alpha_vantage", "pandas"],
                        "全球": ["pandas", "alpha_vantage", "yfinance"]
                    },
                    "settings": {
                        "max_retries": 3,
                        "timeout": 5,
                        "cache_ttl": 60
                    }
                },
                DataCategory.PRICE_DATA.value: {
                    "default_strategy": DataSourceStrategy.RELIABILITY_FIRST.value,
                    "priorities": {
                        "A股": ["pytdx", "easyquotation", "akshare", "qstock", "tushare", "baostock"],
                        "港股": ["akshare", "qstock", "mootdx"],
                        "美股": ["yfinance", "pandas", "alpha_vantage"],
                        "全球": ["yfinance", "pandas", "alpha_vantage"]
                    },
                    "settings": {
                        "max_retries": 2,
                        "timeout": 8,
                        "cache_ttl": 30
                    }
                },
                DataCategory.VOLUME_DATA.value: {
                    "default_strategy": DataSourceStrategy.SPEED_FIRST.value,
                    "priorities": {
                        "A股": ["pytdx", "easyquotation", "akshare", "qstock", "tushare"],
                        "港股": ["akshare", "qstock", "mootdx"],
                        "美股": ["yfinance", "alpha_vantage"]
                    },
                    "settings": {
                        "max_retries": 3,
                        "timeout": 3,
                        "cache_ttl": 60
                    }
                },
                DataCategory.COMPANY_DATA.value: {
                    "default_strategy": DataSourceStrategy.ACCURACY_FIRST.value,
                    "priorities": {
                        "A股": ["akshare", "tushare", "baostock"],
                        "港股": ["akshare", "mootdx"],
                        "美股": ["yfinance", "alpha_vantage", "pandas"]
                    },
                    "settings": {
                        "max_retries": 2,
                        "timeout": 10,
                        "cache_ttl": 3600
                    }
                },
                DataCategory.FINANCIAL_DATA.value: {
                    "default_strategy": DataSourceStrategy.ACCURACY_FIRST.value,
                    "priorities": {
                        "A股": ["qstock", "akshare", "tushare", "baostock"],
                        "港股": ["qstock", "akshare", "mootdx"],
                        "美股": ["yfinance", "alpha_vantage", "pandas"]
                    },
                    "settings": {
                        "max_retries": 2,
                        "timeout": 15,
                        "cache_ttl": 86400
                    }
                },
                DataCategory.TECHNICAL_DATA.value: {
                    "default_strategy": DataSourceStrategy.BALANCED.value,
                    "priorities": {
                        "A股": ["akshare", "tushare"],
                        "港股": ["akshare", "mootdx"],
                        "美股": ["yfinance", "pandas", "alpha_vantage"]
                    },
                    "settings": {
                        "max_retries": 3,
                        "timeout": 8,
                        "cache_ttl": 300
                    }
                }
            },
            "source_metadata": {
                "akshare": {
                    "name": "AKShare",
                    "description": "中国金融数据接口库",
                    "cost": "免费",
                    "rate_limit": "100次/分钟",
                    "reliability": "高",
                    "accuracy": "高",
                    "speed": "快",
                    "data_types": ["实时行情", "历史数据", "财务数据", "技术指标"],
                    "markets": ["A股", "港股", "美股"],
                    "last_updated": datetime.now().isoformat()
                },
                "yfinance": {
                    "name": "Yahoo Finance",
                    "description": "Yahoo Finance数据接口",
                    "cost": "免费",
                    "rate_limit": "2000次/小时",
                    "reliability": "很高",
                    "accuracy": "高",
                    "speed": "快",
                    "data_types": ["实时行情", "历史数据", "财务数据"],
                    "markets": ["美股", "港股", "A股"],
                    "last_updated": datetime.now().isoformat()
                },
                "tushare": {
                    "name": "Tushare",
                    "description": "Tushare金融数据接口",
                    "cost": "付费(积分)",
                    "rate_limit": "500次/天(免费)",
                    "reliability": "很高",
                    "accuracy": "很高",
                    "speed": "快",
                    "data_types": ["实时行情", "历史数据", "财务数据", "板块数据"],
                    "markets": ["A股", "港股"],
                    "last_updated": datetime.now().isoformat()
                },
                "alpha_vantage": {
                    "name": "Alpha Vantage",
                    "description": "Alpha Vantage金融数据API",
                    "cost": "付费",
                    "rate_limit": "500次/天(免费)",
                    "reliability": "高",
                    "accuracy": "很高",
                    "speed": "中等",
                    "data_types": ["实时行情", "历史数据", "技术指标", "财务数据"],
                    "markets": ["美股"],
                    "last_updated": datetime.now().isoformat()
                },
                "mootdx": {
                    "name": "MooTDX",
                    "description": "通达信数据接口",
                    "cost": "免费",
                    "rate_limit": "1000次/分钟",
                    "reliability": "高",
                    "accuracy": "高",
                    "speed": "快",
                    "data_types": ["实时行情", "历史数据", "分笔数据"],
                    "markets": ["A股", "港股", "美股"],
                    "last_updated": datetime.now().isoformat()
                },
                "baostock": {
                    "name": "BaoStock",
                    "description": "证券宝金融数据平台",
                    "cost": "免费",
                    "rate_limit": "无限制",
                    "reliability": "高",
                    "accuracy": "高",
                    "speed": "中等",
                    "data_types": ["历史数据", "财务数据"],
                    "markets": ["A股"],
                    "last_updated": datetime.now().isoformat()
                },
                "pandas": {
                    "name": "Pandas DataReader",
                    "description": "Pandas数据读取器",
                    "cost": "免费",
                    "rate_limit": "限制较少",
                    "reliability": "中等",
                    "accuracy": "中等",
                    "speed": "慢",
                    "data_types": ["历史数据", "财务数据", "宏观数据"],
                    "markets": ["美股", "全球"],
                    "last_updated": datetime.now().isoformat()
                },
                "easyquotation": {
                    "name": "EasyQuotation",
                    "description": "简单易用的行情接口库",
                    "cost": "免费",
                    "rate_limit": "无明确限制",
                    "reliability": "高",
                    "accuracy": "高",
                    "speed": "很快",
                    "data_types": ["实时行情", "基础数据"],
                    "markets": ["A股"],
                    "last_updated": datetime.now().isoformat()
                },
                "qstock": {
                    "name": "QStock",
                    "description": "专业股票数据获取库",
                    "cost": "免费",
                    "rate_limit": "1000次/分钟",
                    "reliability": "高",
                    "accuracy": "高",
                    "speed": "快",
                    "data_types": ["实时行情", "历史数据", "财务数据", "技术指标"],
                    "markets": ["A股", "港股"],
                    "last_updated": datetime.now().isoformat()
                },
                "pytdx": {
                    "name": "PyTDX",
                    "description": "通达信数据接口Python版",
                    "cost": "免费",
                    "rate_limit": "无限制",
                    "reliability": "很高",
                    "accuracy": "很高",
                    "speed": "极快",
                    "data_types": ["实时行情", "历史数据", "分笔数据", "K线数据"],
                    "markets": ["A股"],
                    "last_updated": datetime.now().isoformat()
                }
            },
            "strategy_profiles": {
                DataSourceStrategy.SPEED_FIRST.value: {
                    "description": "速度优先策略",
                    "criteria": ["速度", "实时性"],
                    "weight": {
                        "speed": 0.5,
                        "reliability": 0.2,
                        "accuracy": 0.2,
                        "cost": 0.1
                    }
                },
                DataSourceStrategy.COST_FIRST.value: {
                    "description": "成本优先策略",
                    "criteria": ["成本"],
                    "weight": {
                        "cost": 0.6,
                        "speed": 0.2,
                        "reliability": 0.15,
                        "accuracy": 0.05
                    }
                },
                DataSourceStrategy.RELIABILITY_FIRST.value: {
                    "description": "可靠性优先策略",
                    "criteria": ["可靠性", "稳定性"],
                    "weight": {
                        "reliability": 0.5,
                        "accuracy": 0.25,
                        "speed": 0.15,
                        "cost": 0.1
                    }
                },
                DataSourceStrategy.ACCURACY_FIRST.value: {
                    "description": "精度优先策略",
                    "criteria": ["准确性", "数据质量"],
                    "weight": {
                        "accuracy": 0.5,
                        "reliability": 0.3,
                        "speed": 0.15,
                        "cost": 0.05
                    }
                },
                DataSourceStrategy.BALANCED.value: {
                    "description": "平衡策略",
                    "criteria": ["综合评估"],
                    "weight": {
                        "reliability": 0.25,
                        "accuracy": 0.25,
                        "speed": 0.25,
                        "cost": 0.25
                    }
                }
            }
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    # 合并默认配置和保存的配置
                    return self._merge_config(default_config, saved_config)
            except Exception as e:
                print(f"加载配置文件失败: {e}, 使用默认配置")

        return default_config

    def _merge_config(self, default: Dict, saved: Dict) -> Dict:
        """合并配置"""
        merged = default.copy()
        for key, value in saved.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_config(merged[key], value)
            else:
                merged[key] = value
        return merged

    def save_config(self):
        """保存配置到文件"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False

    def get_priority_sources(self, category: DataCategory, market: str, strategy: Optional[str] = None) -> List[str]:
        """获取指定分类、市场和策略的数据源优先级"""
        if category.value not in self.config["strategies"]:
            return []

        category_config = self.config["strategies"][category.value]

        # 使用指定策略或默认策略
        current_strategy = strategy or category_config.get("default_strategy", DataSourceStrategy.BALANCED.value)

        # 根据策略重新排序数据源
        priorities = category_config.get("priorities", {}).get(market, [])

        if current_strategy == DataSourceStrategy.BALANCED.value:
            return priorities
        else:
            # 根据策略权重重新排序
            return self._sort_sources_by_strategy(priorities, current_strategy)

    def _sort_sources_by_strategy(self, sources: List[str], strategy: str) -> List[str]:
        """根据策略权重重新排序数据源"""
        if strategy not in self.config["strategy_profiles"]:
            return sources

        strategy_config = self.config["strategy_profiles"][strategy]
        weights = strategy_config.get("weight", {})

        source_scores = []
        for source in sources:
            if source in self.config["source_metadata"]:
                metadata = self.config["source_metadata"][source]
                score = 0

                # 计算综合得分
                if "speed" in weights:
                    speed_score = self._convert_rating_to_score(metadata.get("speed", "中等"))
                    score += speed_score * weights["speed"]

                if "reliability" in weights:
                    reliability_score = self._convert_rating_to_score(metadata.get("reliability", "高"))
                    score += reliability_score * weights["reliability"]

                if "accuracy" in weights:
                    accuracy_score = self._convert_rating_to_score(metadata.get("accuracy", "高"))
                    score += accuracy_score * weights["accuracy"]

                if "cost" in weights:
                    cost_score = self._convert_cost_to_score(metadata.get("cost", "免费"))
                    score += cost_score * weights["cost"]

                source_scores.append((source, score))

        # 按得分排序（从高到低）
        source_scores.sort(key=lambda x: x[1], reverse=True)
        return [source for source, _ in source_scores]

    def _convert_rating_to_score(self, rating: str) -> float:
        """将评级转换为分数"""
        rating_scores = {
            "很高": 5.0,
            "高": 4.0,
            "中等": 3.0,
            "低": 2.0,
            "很低": 1.0,
            "快": 4.5,
            "中等": 3.0,
            "慢": 1.5
        }
        return rating_scores.get(rating, 3.0)

    def _convert_cost_to_score(self, cost: str) -> float:
        """将成本转换为分数（成本越低分数越高）"""
        cost_scores = {
            "免费": 5.0,
            "付费": 2.0,
            "付费(积分)": 3.5,
            "付费(订阅)": 2.5
        }
        return cost_scores.get(cost, 3.0)

    def get_source_settings(self, category: DataCategory) -> Dict[str, Any]:
        """获取数据源设置"""
        return self.config["strategies"].get(category.value, {}).get("settings", {})

    def get_source_metadata(self, source: str) -> Dict[str, Any]:
        """获取数据源元数据"""
        return self.config["source_metadata"].get(source, {})

    def get_all_strategies(self) -> Dict[str, Any]:
        """获取所有可用策略"""
        return self.config["strategy_profiles"]

    def update_source_priority(self, category: DataCategory, market: str, priorities: List[str]):
        """更新数据源优先级"""
        if category.value not in self.config["strategies"]:
            self.config["strategies"][category.value] = {}

        if "priorities" not in self.config["strategies"][category.value]:
            self.config["strategies"][category.value]["priorities"] = {}

        self.config["strategies"][category.value]["priorities"][market] = priorities
        self.save_config()

    def update_category_strategy(self, category: DataCategory, strategy: str):
        """更新数据分类的默认策略"""
        if category.value in self.config["strategies"]:
            self.config["strategies"][category.value]["default_strategy"] = strategy
            self.save_config()

    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要"""
        summary = {
            "total_sources": len(self.config["source_metadata"]),
            "total_categories": len(self.config["strategies"]),
            "available_strategies": list(self.config["strategy_profiles"].keys()),
            "categories_config": {}
        }

        for category, config in self.config["strategies"].items():
            summary["categories_config"][category] = {
                "default_strategy": config.get("default_strategy"),
                "market_coverage": list(config.get("priorities", {}).keys()),
                "settings": config.get("settings", {})
            }

        return summary