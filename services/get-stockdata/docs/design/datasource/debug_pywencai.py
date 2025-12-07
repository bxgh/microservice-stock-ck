# -*- coding: utf-8 -*-
"""
pywencai调试脚本
用于测试pywencai的基本功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pywencai
import pandas as pd
from Common import baseWencai as wenCai

def test_basic_pywencai():
    """测试基本的pywencai功能"""
    print("=== 测试基本pywencai功能 ===")
    try:
        # 简单查询
        query = '平安银行'
        print(f"查询: {query}")
        res = pywencai.get(query=query)
        print(f"查询结果类型: {type(res)}")
        if res is not None:
            if isinstance(res, dict):
                print("查询结果是字典格式:")
                for key, value in res.items():
                    print(f"  {key}: {type(value)}")
                    if isinstance(value, pd.DataFrame):
                        print(f"    DataFrame形状: {value.shape}")
                        print(f"    列名: {value.columns.tolist()}")
                        if not value.empty:
                            print("    前3行数据:")
                            print(value.head(3))
            elif isinstance(res, pd.DataFrame):
                print(f"查询结果是DataFrame格式")
                print(f"查询结果形状: {res.shape}")
                print(f"查询结果列名: {res.columns.tolist()}")
                print("前5行数据:")
                print(res.head())
            else:
                print(f"查询结果是其他格式: {type(res)}")
                print(f"内容: {res}")
        else:
            print("查询结果为None")
        print("-" * 50)
    except Exception as e:
        print(f"基本查询失败: {e}")
        import traceback
        traceback.print_exc()

def test_wencai_module():
    """测试自定义的wencai模块"""
    print("=== 测试自定义wencai模块 ===")
    try:
        # 使用项目中的wencai模块
        query = "平安银行"
        query_type = "stock"
        print(f"查询: {query}")
        res = wenCai.wencai(query, query_type)
        print(f"查询结果类型: {type(res)}")
        if res is not None:
            if isinstance(res, dict):
                print("查询结果是字典格式:")
                for key, value in res.items():
                    print(f"  {key}: {type(value)}")
                    if isinstance(value, pd.DataFrame):
                        print(f"    DataFrame形状: {value.shape}")
                        print(f"    列名: {value.columns.tolist()}")
                        if not value.empty:
                            print("    前3行数据:")
                            print(value.head(3))
            elif isinstance(res, pd.DataFrame):
                print(f"查询结果是DataFrame格式")
                print(f"查询结果形状: {res.shape}")
                print(f"查询结果列名: {res.columns.tolist()}")
                print("前5行数据:")
                print(res.head())
            else:
                print(f"查询结果是其他格式: {type(res)}")
                print(f"内容: {res}")
        else:
            print("查询结果为None")
        print("-" * 50)
    except Exception as e:
        print(f"wencai模块查询失败: {e}")
        import traceback
        traceback.print_exc()

def test_different_queries():
    """测试不同的查询类型"""
    print("=== 测试不同查询类型 ===")

    test_queries = [
        ("平安银行", "stock"),
        ("概念板块", "zhishu"),
        ("涨幅榜", "stock"),
        ("成交量排行", "stock"),
    ]

    for query, query_type in test_queries:
        try:
            print(f"\n查询: {query} (类型: {query_type})")
            res = pywencai.get(query=query, query_type=query_type, perpage=5)
            if res is not None:
                if isinstance(res, dict):
                    print("[成功] 结果是字典格式")
                    for key, value in res.items():
                        if isinstance(value, pd.DataFrame) and not value.empty:
                            print(f"  DataFrame '{key}' 形状: {value.shape}")
                            print(f"  列名: {value.columns.tolist()[:3]}...")
                elif isinstance(res, pd.DataFrame):
                    if not res.empty:
                        print(f"[成功] 结果形状: {res.shape}")
                        print(f"列名: {res.columns.tolist()[:3]}...")
                    else:
                        print("[空] 查询结果为空DataFrame")
                else:
                    print(f"[其他] 结果类型: {type(res)}")
            else:
                print("[空] 查询结果为None")
        except Exception as e:
            print(f"[失败] 查询失败: {e}")

def main():
    print("pywencai调试开始...")
    print(f"Python版本: {sys.version}")
    print(f"pywencai版本: {pywencai.__version__ if hasattr(pywencai, '__version__') else '未知'}")
    print("-" * 50)

    # 测试基本功能
    test_basic_pywencai()

    # 测试自定义模块
    test_wencai_module()

    # 测试不同查询
    test_different_queries()

    print("\n调试完成!")

if __name__ == "__main__":
    main()