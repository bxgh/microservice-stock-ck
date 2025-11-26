#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
mootdx连接管理
提取自fenbi.py的已验证连接逻辑
"""

import time
import pandas as pd
from typing import Optional, List
from datetime import datetime

try:
    from mootdx.quotes import Quotes
except ImportError:
    print("错误：无法导入mootdx库，请确保已正确安装")
    print("安装命令：pip install mootdx")
    Quotes = None


class MootdxConnection:
    """mootdx连接管理器"""

    def __init__(self, timeout: int = 60, best_ip: bool = True):
        """
        初始化mootdx连接

        Args:
            timeout: 连接超时时间
            best_ip: 是否使用最佳IP
        """
        self.timeout = timeout
        self.best_ip = best_ip
        self.client: Optional[Quotes] = None
        self._connected = False
        self._connect_time: Optional[datetime] = None

    async def connect(self) -> bool:
        """
        连接到mootdx服务器
        复用成功文件验证的连接逻辑

        Returns:
            bool: 连接是否成功
        """
        if Quotes is None:
            print("错误：mootdx库未安装")
            return False

        try:
            # 首先运行bestip获取最佳服务器
            import subprocess
            import sys
            print("[INFO] 正在获取最佳服务器...")
            try:
                result = subprocess.run([sys.executable, "-m", "mootdx", "bestip"],
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    print("[OK] 最佳服务器配置完成")
                else:
                    print(f"[WARN] bestip配置警告: {result.stderr}")
            except subprocess.TimeoutExpired:
                print("[WARN] bestip配置超时，使用默认配置")
            except Exception as e:
                print(f"[WARN] bestip配置失败: {e}")

            # 使用成功文件中完全相同的参数
            self.client = Quotes.factory(
                market='std',
                multithread=True,
                heartbeat=True,
                block=False
            )

            # 测试连接 - 等待服务器选择完成
            import asyncio
            await asyncio.sleep(2)  # 给服务器选择更多时间

            if self.client:
                self._connected = True
                self._connect_time = datetime.now()
                print(f"[OK] 成功连接到mootdx服务器")
                return True
            else:
                print("[ERROR] 创建mootdx客户端失败")
                return False

        except Exception as e:
            import traceback
            print(f"[ERROR] 连接mootdx服务器失败: {e}")
            traceback.print_exc()
            self._connected = False
            return False

    def fetch_transactions(self, symbol: str, date: str, start: int, count: int) -> pd.DataFrame:
        """
        获取分笔数据
        复用fenbi.py已验证的获取逻辑

        Args:
            symbol: 股票代码
            date: 日期 (YYYYMMDD)
            start: 起始位置
            count: 获取数量

        Returns:
            pd.DataFrame: 分笔数据
        """
        if not self._connected or not self.client:
            return pd.DataFrame()

        try:
            df = self.client.transactions(symbol=symbol, date=date, start=start, count=count)

            if df is None or df.empty:
                return pd.DataFrame()

            return df

        except Exception as e:
            print(f"[ERROR] 获取分笔数据失败: {e}")
            return pd.DataFrame()

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected

    @property
    def connect_time(self) -> Optional[datetime]:
        """连接时间"""
        return self._connect_time

    async def close(self):
        """关闭连接"""
        if self.client:
            try:
                self.client.close()
                print("[OK] 已关闭mootdx连接")
            except:
                pass
            finally:
                self.client = None
                self._connected = False