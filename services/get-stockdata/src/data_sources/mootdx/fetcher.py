#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
mootdx数据获取器
实现数据源基类，封装fenbi.py的核心获取策略
"""

import asyncio
import time
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, time as dt_time
from concurrent.futures import ThreadPoolExecutor

try:
    from ..base import DataSourceBase
    from ....models.tick_models import TickData, TickDataRequest
except ImportError:
    from data_sources.base import DataSourceBase
    from models.tick_models import TickData, TickDataRequest

from .connection import MootdxConnection


class MootdxDataSource(DataSourceBase):
    """mootdx数据源实现，基于fenbi.py已验证的逻辑"""

    def __init__(self,
                 timeout: int = 60,
                 best_ip: bool = True,
                 overlap_ratio: float = 0.2,
                 batch_size: int = 800,
                 max_records: int = 200000,
                 max_consecutive_empty: int = 5):
        """
        初始化mootdx数据源

        Args:
            timeout: 连接超时时间
            best_ip: 是否使用最佳IP
            overlap_ratio: 重叠比例
            batch_size: 批次大小
            max_records: 最大记录数
            max_consecutive_empty: 最大连续空返回次数
        """
        self.connection = MootdxConnection(timeout=timeout, best_ip=best_ip)
        self.overlap_ratio = max(0.1, min(0.3, overlap_ratio))  # 限制在10%-30%
        self.batch_size = batch_size
        self.max_records = max_records
        self.max_consecutive_empty = max_consecutive_empty

        # 统计信息
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'duplicate_records': 0,
            'start_time': None,
            'end_time': None
        }

        self._executor = ThreadPoolExecutor(max_workers=1)

    @property
    def source_name(self) -> str:
        """数据源名称"""
        return "mootdx"

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self.connection.is_connected

    async def connect(self) -> bool:
        """连接数据源"""
        return await self.connection.connect()

    async def get_tick_data(self, request: TickDataRequest) -> List[TickData]:
        """
        获取分笔数据
        调用fenbi.py的多起始位置策略，返回标准格式

        Args:
            request: 分笔数据请求

        Returns:
            List[TickData]: 分笔数据列表
        """
        df = await self.get_tick_data_dataframe(request)
        return self._dataframe_to_tickdata(df, request.stock_code, request.date)

    async def get_tick_data_dataframe(self, request: TickDataRequest) -> pd.DataFrame:
        """
        获取分笔数据(DataFrame格式)
        使用反向爬取策略：start=0为最新数据，递增start获取更早数据
        """
        if not self.is_connected:
            if not await self.connect():
                return pd.DataFrame()

        symbol = request.stock_code
        date_str = request.date.strftime('%Y%m%d')
        
        print(f"\n🚀 开始获取分笔数据: {symbol} {date_str}")
        print(f"ℹ️ 策略: 反向爬取 (Start=0 -> End of Day)")

        self.stats['start_time'] = datetime.now()
        
        all_data = []
        seen_keys = set()
        
        # 初始参数
        current_start = 0
        batch_size = 2000 # 请求大一点，但服务器可能只返回800
        max_empty_retries = 3
        empty_count = 0
        
        # 目标时间：09:25
        target_reached = False
        
        while True:
            print(f"📥 获取批次: Start={current_start}")
            
            try:
                batch_data = await self._fetch_batch(symbol, date_str, current_start, batch_size)
                
                if batch_data.empty:
                    empty_count += 1
                    print(f"⚠️ 空数据返回 ({empty_count}/{max_empty_retries})")
                    if empty_count >= max_empty_retries:
                        print("🛑 连续空数据，停止获取")
                        break
                    current_start += 800 # 尝试跳过
                    continue
                
                empty_count = 0 # 重置计数
                
                # 记录数
                count = len(batch_data)
                earliest_time = str(batch_data['time'].iloc[0]) # 假设返回是升序，或者我们需要检查
                latest_time = str(batch_data['time'].iloc[-1])
                
                # 检查数据顺序
                # 根据测试，mootdx返回的数据在批次内可能是升序的，但批次间是倒序的
                # Start=0: 14:16 - 15:00
                # Start=2000: 11:01 - 13:11
                
                print(f"📊 批次数据: {count}条, 时间: {earliest_time} - {latest_time}")
                
                # 添加数据
                new_data = []
                for _, row in batch_data.iterrows():
                    key = f"{row['time']}_{row['price']}_{row['volume']}"
                    if key not in seen_keys:
                        seen_keys.add(key)
                        new_data.append(row)
                
                if new_data:
                    all_data.extend(new_data)
                    
                    # 检查是否到达开盘时间
                    # 找出本批次中最早的时间
                    batch_times = sorted([str(t) for t in batch_data['time']])
                    batch_earliest = batch_times[0]
                    
                    if batch_earliest <= "09:25":
                        print(f"✅ 已到达开盘时间 ({batch_earliest})，停止获取")
                        target_reached = True
                        break
                
                # 准备下一批次
                # 实际上mootdx似乎每页800条，所以我们递增800
                # 即使请求2000，它也只给800
                current_start += 800
                
                # 安全限制
                if current_start > 20000:
                    print("🛑 达到最大深度限制，停止获取")
                    break
                    
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"❌ 获取失败: {e}")
                break

        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

        if all_data:
            final_data = pd.DataFrame(all_data)
            
            # 最终去重
            final_data = final_data.drop_duplicates(subset=['time', 'price', 'volume'])
            
            # 按时间升序排列
            final_data = final_data.sort_values('time', ascending=True).reset_index(drop=True)
            
            # 添加元数据
            final_data['symbol'] = symbol
            final_data['date'] = date_str
            final_data['cumulative_volume'] = final_data['volume'].cumsum()
            
            earliest = str(final_data['time'].iloc[0])
            latest = str(final_data['time'].iloc[-1])
            
            print(f"\n🔥 获取完成: {len(final_data)}条记录, 用时{duration:.2f}s")
            print(f"⏰ 最终范围: {earliest} - {latest}")
            
            return final_data
        else:
            print(f"\n❌ 未获取到任何数据")
            return pd.DataFrame()
  
    async def _fetch_batch(self, symbol: str, date: str, start: int, count: int) -> pd.DataFrame:
        """
        批量获取数据
        在线程池中执行同步调用

        Args:
            symbol: 股票代码
            date: 日期
            start: 起始位置
            count: 获取数量

        Returns:
            pd.DataFrame: 批量数据
        """
        self.stats['total_requests'] += 1

        try:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                self._executor,
                self.connection.fetch_transactions,
                symbol, date, start, count
            )

            if not df.empty:
                self.stats['successful_requests'] += 1

            return df

        except Exception as e:
            print(f"  [ERROR] 获取失败: {e}")
            return pd.DataFrame()

    def _dataframe_to_tickdata(self, df: pd.DataFrame, symbol: str, date: datetime) -> List[TickData]:
        """
        将DataFrame转换为TickData列表

        Args:
            df: 分笔数据DataFrame
            symbol: 股票代码
            date: 日期

        Returns:
            List[TickData]: TickData列表
        """
        if df.empty:
            return []

        tick_data_list = []
        for _, row in df.iterrows():
            try:
                # 解析时间
                time_str = str(row['time'])
                if ':' in time_str:
                    if len(time_str.split(':')) == 2:
                        time_obj = datetime.strptime(f"{date.strftime('%Y%m%d')} {time_str}", "%Y%m%d %H:%M")
                    else:
                        time_obj = datetime.strptime(f"{date.strftime('%Y%m%d')} {time_str}", "%Y%m%d %H:%M:%S")
                else:
                    continue

                tick_data = TickData(
                    time=time_obj,
                    price=float(row['price']),
                    volume=int(row['volume']),
                    amount=float(row['price']) * int(row.get('volume', 0)),
                    direction=self._convert_direction(row.get('buyorsell', 2)),
                    code=symbol,
                    date=date
                )
                tick_data_list.append(tick_data)

            except Exception as e:
                print(f"  [WARN] 转换数据失败: {e}")
                continue

        return tick_data_list

    def _convert_direction(self, buyorsell: int) -> str:
        """转换买卖方向"""
        if buyorsell == 1:
            return 'B'  # 买入
        elif buyorsell == 0:
            return 'S'  # 卖出
        else:
            return 'N'  # 中性

    def _sort_data_by_time(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        按时间排序数据
        复用fenbi.py的排序逻辑

        Args:
            df: 原始数据

        Returns:
            pd.DataFrame: 排序后数据
        """
        if df.empty or 'time' not in df.columns:
            return df

        try:
            # 支持多种时间格式进行排序
            times_hms = pd.to_datetime(df['time'], format='%H:%M:%S', errors='coerce')
            times_hm = pd.to_datetime(df['time'], format='%H:%M', errors='coerce')
            sorted_times = times_hms.fillna(times_hm)

            df_copy = df.copy()
            df_copy['sort_time'] = sorted_times

            df_sorted = df_copy.sort_values('sort_time').drop('sort_time', axis=1)
            df_sorted = df_sorted.reset_index(drop=True)

            return df_sorted

        except Exception as e:
            print(f"[WARN] 数据排序失败，使用原始顺序: {e}")
            return df

    async def get_status(self) -> Dict[str, Any]:
        """获取数据源状态"""
        return {
            "source_name": self.source_name,
            "is_connected": self.is_connected,
            "connect_time": self.connection.connect_time,
            "stats": self.stats.copy()
        }

    async def close(self):
        """关闭连接"""
        await self.connection.close()
        self._executor.shutdown(wait=True)