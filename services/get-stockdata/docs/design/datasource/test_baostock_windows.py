# -*- coding: utf-8 -*-
"""
在Windows Python 3.11环境中测试baostock
"""
import baostock as bs
import pandas as pd
import sys
from datetime import datetime

def test_baostock_windows():
    """在Windows环境中测试baostock功能"""
    print("=== baostock Windows环境测试 ===")
    print(f"测试时间: {datetime.now()}")
    print(f"Python版本: {sys.version}")

    try:
        print(f"baostock版本: {bs.__version__}")
        print("baostock导入成功")
    except Exception as e:
        print(f"baostock导入失败: {e}")
        return

    # 测试1: 登录连接
    print("\n1. 测试登录连接...")
    try:
        lg = bs.login()
        print(f"登录结果: {lg.error_code}")
        print(f"登录信息: {lg.error_msg}")

        if lg.error_code == '0':
            print("[成功] baostock连接成功")
            login_success = True
        else:
            print(f"[失败] baostock连接失败: {lg.error_msg}")
            login_success = False
            return

    except Exception as e:
        print(f"[异常] 登录过程异常: {e}")
        return

    # 测试2: 获取股票基本信息
    print("\n2. 测试股票基本信息...")
    try:
        rs = bs.query_stock_basic()
        print(f"查询结果: {rs.error_code}")

        if rs.error_code == '0':
            data_list = []
            count = 0
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
                count += 1
                if count >= 100:  # 只获取前100条
                    break

            df = pd.DataFrame(data_list, columns=rs.fields)
            print(f"[成功] 获取股票基本信息: {count} 条")
            print("数据列名:", df.columns.tolist())
            print("前5条数据:")
            for i, row in df.head().iterrows():
                print(f"  {row['code']} {row['code_name']} {row['type']}")
        else:
            print(f"[失败] 查询失败: {rs.error_msg}")

    except Exception as e:
        print(f"[异常] 获取基本信息异常: {e}")

    # 测试3: 历史K线数据
    print("\n3. 测试历史K线数据...")
    test_stocks = [
        ("sh.600000", "浦发银行"),
        ("sz.000001", "平安银行"),
        ("sh.600036", "招商银行")
    ]

    for code, name in test_stocks:
        try:
            print(f"\n测试 {name}({code}):")

            rs = bs.query_history_k_data_plus(
                code=code,
                start_date='2024-12-01',
                end_date='2024-12-06',
                frequency="d",
                fields="date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST"
            )

            print(f"查询结果: {rs.error_code}")

            if rs.error_code == '0':
                data_list = []
                while (rs.error_code == '0') & rs.next():
                    data_list.append(rs.get_row_data())

                df = pd.DataFrame(data_list, columns=rs.fields)
                print(f"[成功] {name} 历史数据: {len(df)} 条")

                if len(df) > 0:
                    print("最新数据:")
                    latest = df.iloc[-1]
                    print(f"  日期: {latest['date']}")
                    print(f"  开盘: {latest['open']}")
                    print(f"  最高: {latest['high']}")
                    print(f"  最低: {latest['low']}")
                    print(f"  收盘: {latest['close']}")
                    print(f"  涨跌幅: {latest['pctChg']}%")
            else:
                print(f"[失败] 查询失败: {rs.error_msg}")

        except Exception as e:
            print(f"[异常] {name}测试异常: {e}")

    # 测试4: 指数数据
    print("\n4. 测试指数数据...")
    try:
        rs = bs.query_history_k_data_plus(
            code="sh.000001",  # 上证指数
            start_date='2024-12-01',
            end_date='2024-12-06',
            frequency="d",
            fields="date,code,open,high,low,close,volume,amount"
        )

        if rs.error_code == '0':
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            df = pd.DataFrame(data_list, columns=rs.fields)
            print(f"[成功] 上证指数数据: {len(df)} 条")
            if len(df) > 0:
                print("最新指数:")
                latest = df.iloc[-1]
                print(f"  日期: {latest['date']}")
                print(f"  收盘: {latest['close']}")
                print(f"  成交量: {latest['volume']}")
        else:
            print(f"[失败] 指数查询失败: {rs.error_msg}")

    except Exception as e:
        print(f"[异常] 指数数据测试异常: {e}")

    # 测试5: 行业数据
    print("\n5. 测试行业数据...")
    try:
        rs = bs.query_stock_industry()
        if rs.error_code == '0':
            industry_count = 0
            industries = set()
            sample_data = []

            while (rs.error_code == '0') & rs.next():
                industry_count += 1
                row_data = rs.get_row_data()
                if len(row_data) > 1:
                    industries.add(row_data[1])
                if len(sample_data) < 5:
                    sample_data.append(row_data)

            print(f"[成功] 行业数据: {industry_count} 条")
            print(f"涉及行业数量: {len(industries)}")
            print("部分行业:", list(industries)[:10])
            print("示例数据:")
            for row in sample_data:
                print(f"  {row}")
        else:
            print(f"[失败] 行业数据查询失败: {rs.error_msg}")

    except Exception as e:
        print(f"[异常] 行业数据测试异常: {e}")

    # 登出
    print("\n6. 登出...")
    try:
        logout_rs = bs.logout()
        print(f"登出结果: {logout_rs.error_code}")
        print("[成功] 测试完成")
    except Exception as e:
        print(f"[异常] 登出异常: {e}")

def main():
    test_baostock_windows()

if __name__ == "__main__":
    main()