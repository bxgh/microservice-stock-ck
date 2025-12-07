# -*- coding: utf-8 -*-
"""
pywencai使用示例
展示如何正确使用pywencai获取股票和指数数据
"""
import pywencai
import pandas as pd

def get_stock_basic_info(stock_name):
    """获取股票基本信息"""
    try:
        result = pywencai.get(query=stock_name)

        # pywencai返回的是字典格式，包含多个DataFrame
        if isinstance(result, dict):
            # 获取股票代码和基本信息
            if 'kline2' in result and not result['kline2'].empty:
                stock_data = result['kline2'].iloc[0]
                return {
                    '股票代码': stock_data.get('code', ''),
                    '股票名称': stock_data.get('股票名称', ''),
                    '最新价(元)': stock_data.get('最新价(元)', ''),
                    '股票简称': stock_data.get('股票简称', '')
                }
        return None
    except Exception as e:
        print(f"获取股票信息失败: {e}")
        return None

def get_stock_list(query, perpage=10):
    """获取股票列表"""
    try:
        result = pywencai.get(query=query, perpage=perpage)

        if isinstance(result, pd.DataFrame):
            return result
        elif isinstance(result, dict):
            # 查找主要的数据表
            for key, value in result.items():
                if isinstance(value, pd.DataFrame) and not value.empty:
                    # 如果包含股票代码列，认为这是主要的股票列表
                    if any('代码' in col for col in value.columns):
                        return value
            return None
        return None
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return None

def main():
    print("=== pywencai使用示例 ===\n")

    # 示例1: 获取单只股票基本信息
    print("1. 获取平安银行基本信息:")
    stock_info = get_stock_basic_info("平安银行")
    if stock_info:
        for key, value in stock_info.items():
            print(f"   {key}: {value}")
    print()

    # 示例2: 获取股票列表
    print("2. 获取涨幅榜前5名:")
    top_stocks = get_stock_list("涨幅榜", perpage=5)
    if top_stocks is not None:
        print(f"   查询到 {len(top_stocks)} 只股票")
        # 显示主要的列
        main_columns = [col for col in top_stocks.columns[:6]]  # 显示前6列
        print(f"   主要列名: {main_columns}")
        if not top_stocks.empty:
            print("   前几行数据:")
            print(top_stocks[main_columns].head())
    print()

    # 示例3: 获取概念股
    print("3. 获取人工智能概念股:")
    concept_stocks = get_stock_list("人工智能", perpage=5)
    if concept_stocks is not None:
        print(f"   查询到 {len(concept_stocks)} 只概念股")
        main_columns = [col for col in concept_stocks.columns[:6]]
        if not concept_stocks.empty and len(main_columns) > 0:
            print("   前几行数据:")
            print(concept_stocks[main_columns].head())
    print()

    # 示例4: 获取指数信息
    print("4. 获取上证指数信息:")
    try:
        index_result = pywencai.get(query="上证指数", query_type="zhishu")
        if isinstance(index_result, pd.DataFrame) and not index_result.empty:
            print(f"   指数数据形状: {index_result.shape}")
            print(f"   列名: {index_result.columns.tolist()}")
        elif isinstance(index_result, dict):
            for key, value in index_result.items():
                if isinstance(value, pd.DataFrame) and not value.empty:
                    print(f"   {key}: {value.shape}")
        else:
            print("   未获取到指数数据")
    except Exception as e:
        print(f"   获取指数信息失败: {e}")

    print("\n=== 使用提示 ===")
    print("1. pywencai的返回值通常是字典格式，包含多个DataFrame")
    print("2. 股票列表查询通常返回DataFrame格式")
    print("3. 单个股票查询返回字典，包含多种数据类型")
    print("4. 使用query_type参数指定查询类型（stock/zhishu等）")
    print("5. 可以使用perpage参数控制返回的数据量")

if __name__ == "__main__":
    main()