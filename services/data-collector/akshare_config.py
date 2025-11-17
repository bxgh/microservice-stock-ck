#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AKShare 可用接口配置文件
基于实际测试结果，定义可用的API接口和配置
"""

import akshare as ak
import pandas as pd
import time
from typing import Optional, Dict, Any, List

class AKShareConfig:
    """AKShare可用接口配置类"""

    # 可用的API接口配置
    AVAILABLE_APIS = {
        # 交易日历类
        'trading_dates': {
            'function': ak.tool_trade_date_hist_sina,
            'name': '交易日期历史数据',
            'source': '新浪财经',
            'response_time': '~0.25s',
            'data_count': 8555,
            'status': '✅ 完全可用',
            'description': '获取中国股市所有交易日期'
        },

        # 指数成分股类
        'index_constituents': {
            'function': ak.index_stock_cons,
            'name': '指数成分股查询',
            'source': '多数据源',
            'response_time': '~0.5s',
            'status': '✅ 完全可用',
            'description': '获取指定指数的成分股信息',
            'supported_indices': {
                '000300': '沪深300',
                '000016': '上证50',
                '000905': '中证500'
            }
        },

        # 基金ETF类
        'etf_spot_ths': {
            'function': ak.fund_etf_spot_ths,
            'name': 'ETF实时数据',
            'source': '同花顺',
            'response_time': '~0.82s',
            'data_count': 1380,
            'status': '✅ 可用'
        },

        'etf_category_sina': {
            'function': ak.fund_etf_category_sina,
            'name': 'ETF分类信息',
            'source': '新浪财经',
            'response_time': '~1.61s',
            'data_count': 361,
            'status': '✅ 可用'
        },

        'etf_hist_sina': {
            'function': ak.fund_etf_hist_sina,
            'name': 'ETF历史数据',
            'source': '新浪财经',
            'response_time': '~0.94s',
            'data_count': 5039,
            'status': '✅ 可用'
        },

        'fund_scale_open_sina': {
            'function': ak.fund_scale_open_sina,
            'name': '开放式基金规模',
            'source': '新浪财经',
            'response_time': '~21.87s',
            'data_count': 6024,
            'status': '✅ 可用'
        },

        'fund_scale_close_sina': {
            'function': ak.fund_scale_close_sina,
            'name': '封闭式基金规模',
            'source': '新浪财经',
            'response_time': '~1.89s',
            'data_count': 177,
            'status': '✅ 可用'
        },

        # 外汇汇率类
        'currency_boc_sina': {
            'function': ak.currency_boc_sina,
            'name': '中国银行外汇汇率',
            'source': '新浪财经',
            'response_time': '~0.92s',
            'data_count': 180,
            'status': '✅ 可用'
        },

        # 债券类
        'bond_cb_profile_sina': {
            'function': ak.bond_cb_profile_sina,
            'name': '可转债基本信息',
            'source': '新浪财经',
            'response_time': '~0.48s',
            'data_count': 25,
            'status': '✅ 可用'
        },

        'bond_cb_summary_sina': {
            'function': ak.bond_cb_summary_sina,
            'name': '可转债汇总信息',
            'source': '新浪财经',
            'response_time': '~0.63s',
            'data_count': 15,
            'status': '✅ 可用'
        },

        'bond_zh_cov_info_ths': {
            'function': ak.bond_zh_cov_info_ths,
            'name': '债券可转债信息',
            'source': '同花顺',
            'response_time': '~0.62s',
            'data_count': 896,
            'status': '✅ 可用'
        },

        # 概念板块类
        'stock_board_concept_name_ths': {
            'function': ak.stock_board_concept_name_ths,
            'name': '概念板块名称',
            'source': '同花顺',
            'response_time': '<0.01s',
            'data_count': 374,
            'status': '✅ 可用'
        },

        'stock_board_concept_index_ths': {
            'function': ak.stock_board_concept_index_ths,
            'name': '概念板块指数',
            'source': '同花顺',
            'response_time': '~9.73s',
            'data_count': 1248,
            'status': '✅ 可用'
        },

        'stock_board_concept_info_ths': {
            'function': ak.stock_board_concept_info_ths,
            'name': '概念板块信息',
            'source': '同花顺',
            'response_time': '~0.22s',
            'data_count': 10,
            'status': '✅ 可用'
        }
    }

    # API调用配置
    API_CONFIG = {
        'max_retries': 3,           # 最大重试次数
        'retry_delay': 1,           # 重试延迟(秒)
        'request_timeout': 30,      # 请求超时(秒)
        'rate_limit_delay': 0.5,    # 请求间隔(秒)
    }

    # 环境信息
    ENVIRONMENT_INFO = {
        'akshare_version': '1.17.85',
        'python_version': '3.12.3',
        'test_date': '2025-11-17',
        'working_sources': ['新浪财经', '同花顺'],
        'failed_sources': ['东方财富', '腾讯财经']
    }

class AKShareManager:
    """AKShare可用接口管理器"""

    def __init__(self):
        self.config = AKShareConfig()
        self.last_call_time = 0

    def safe_api_call(self, api_key: str, *args, **kwargs) -> Optional[pd.DataFrame]:
        """安全的API调用"""
        if api_key not in self.config.AVAILABLE_APIS:
            raise ValueError(f"API '{api_key}' 不在可用列表中")

        api_info = self.config.AVAILABLE_APIS[api_key]
        api_func = api_info['function']

        # 请求频率控制
        current_time = time.time()
        if current_time - self.last_call_time < self.config.API_CONFIG['rate_limit_delay']:
            time.sleep(self.config.API_CONFIG['rate_limit_delay'])

        # 重试机制
        max_retries = self.config.API_CONFIG['max_retries']
        retry_delay = self.config.API_CONFIG['retry_delay']

        for attempt in range(max_retries):
            try:
                print(f"🔍 调用API: {api_info['name']}")
                start_time = time.time()

                result = api_func(*args, **kwargs)

                end_time = time.time()
                print(f"✅ {api_info['name']} - 成功! 耗时: {end_time - start_time:.2f}s")

                if hasattr(result, 'empty') and not result.empty:
                    print(f"   📊 数据量: {len(result)} 条")

                self.last_call_time = time.time()
                return result

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"❌ 第{attempt + 1}次尝试失败: {str(e)[:50]}...")
                    print(f"   ⏳ {retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    print(f"❌ {api_info['name']} - 所有重试均失败")
                    print(f"   最后错误: {str(e)}")
                    return None

    def get_available_apis(self) -> Dict[str, Dict[str, Any]]:
        """获取所有可用API列表"""
        return self.config.AVAILABLE_APIS

    def get_api_info(self, api_key: str) -> Dict[str, Any]:
        """获取指定API信息"""
        return self.config.AVAILABLE_APIS.get(api_key, {})

    def get_environment_info(self) -> Dict[str, Any]:
        """获取环境信息"""
        return self.config.ENVIRONMENT_INFO

# 预定义的便捷函数
def get_trading_dates() -> Optional[pd.DataFrame]:
    """获取交易日期"""
    manager = AKShareManager()
    return manager.safe_api_call('trading_dates')

def get_index_constituents(index_code: str = "000300") -> Optional[pd.DataFrame]:
    """获取指数成分股"""
    manager = AKShareManager()
    return manager.safe_api_call('index_constituents', index_code)

def get_etf_data() -> tuple:
    """获取ETF数据"""
    manager = AKShareManager()
    spot_data = manager.safe_api_call('etf_spot_ths')
    hist_data = manager.safe_api_call('etf_hist_sina')
    return spot_data, hist_data

def get_currency_data() -> Optional[pd.DataFrame]:
    """获取汇率数据"""
    manager = AKShareManager()
    return manager.safe_api_call('currency_boc_sina')

def list_available_apis() -> None:
    """列出所有可用的API"""
    manager = AKShareManager()
    apis = manager.get_available_apis()

    print("📊 AKShare 可用API列表:")
    print("=" * 60)

    for key, info in apis.items():
        print(f"\n🔑 {key}")
        print(f"   📝 名称: {info['name']}")
        print(f"   📡 数据源: {info['source']}")
        print(f"   ⏱️ 响应时间: {info.get('response_time', 'N/A')}")
        print(f"   📊 数据量: {info.get('data_count', 'N/A')} 条")
        print(f"   ✅ 状态: {info['status']}")
        print(f"   📄 描述: {info.get('description', 'N/A')}")

if __name__ == "__main__":
    # 测试配置
    print("🧪 测试AKShare配置...")

    # 显示可用API
    list_available_apis()

    # 测试一个API
    print("\n🧪 测试获取交易日期...")
    dates = get_trading_dates()
    if dates is not None:
        print(f"✅ 成功获取交易日期: {len(dates)} 条")
    else:
        print("❌ 获取交易日期失败")