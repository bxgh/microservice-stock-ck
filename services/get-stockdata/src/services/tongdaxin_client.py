#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
通达信(TongDaXin)数据源客户端
提供通达信行情数据获取服务，专门用于分笔数据获取
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, time, timedelta
import json
import random
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    from mootdx import get_api
    from mootdx.consts import MARKET_SH, MARKET_SZ
except ImportError:
    # 如果mootdx不可用，创建占位符
    get_api = None
    MARKET_SH = 1
    MARKET_SZ = 0

try:
    from ..models.tick_models import (
        TickData, TickDataRequest, TickDataBatchRequest,
        TickDataResponse, TickDataBatchResponse, TickDataSummary,
        DataSourceStatus, TickDataAdapter
    )
    from ..models.stock_models import StockInfo
except ImportError:
    # 测试时使用绝对导入
    from models.tick_models import (
        TickData, TickDataRequest, TickDataBatchRequest,
        TickDataResponse, TickDataBatchResponse, TickDataSummary,
        DataSourceStatus, TickDataAdapter
    )
    from models.stock_models import StockInfo

logger = logging.getLogger(__name__)


class TongDaXinClient:
    """通达信数据源客户端"""

    def __init__(self, max_connections: int = 5, timeout: int = 30):
        """
        初始化通达信客户端

        Args:
            max_connections: 最大连接数
            timeout: 连接超时时间(秒)
        """
        self.max_connections = max_connections
        self.timeout = timeout
        self._connections = []
        self._connection_pool = []
        self._is_connected = False
        self._last_connect_time = None
        self._server_list = [
            ("119.147.212.81", 7709),  # 主服务器
            ("113.105.142.136", 443),  # 备用服务器1
            ("180.153.18.170", 7709),  # 备用服务器2
            ("180.153.18.171", 7709),  # 备用服务器3
            ("218.75.126.9", 7709),   # 备用服务器4
        ]
        self._current_server_index = 0
        self._executor = ThreadPoolExecutor(max_workers=max_connections)
        self._lock = asyncio.Lock()

    async def initialize(self) -> bool:
        """
        初始化连接池

        Returns:
            连接是否成功
        """
        try:
            if get_api is None:
                logger.warning("mootdx库未安装，通达信客户端无法使用")
                return False

            # 测试连接服务器
            for i, (host, port) in enumerate(self._server_list):
                try:
                    logger.info(f"尝试连接通达信服务器 {i+1}/{len(self._server_list)}: {host}:{port}")

                    # 创建连接
                    api = get_api()

                    # 测试连接 (使用同步方式，在executor中执行)
                    success = await asyncio.get_event_loop().run_in_executor(
                        self._executor, self._test_connection, api, host, port
                    )

                    if success:
                        async with self._lock:
                            self._connection_pool.append({
                                'api': api,
                                'host': host,
                                'port': port,
                                'in_use': False,
                                'last_used': datetime.now()
                            })

                        logger.info(f"成功连接到通达信服务器: {host}:{port}")
                        self._current_server_index = i
                        self._is_connected = True
                        self._last_connect_time = datetime.now()
                        return True
                    else:
                        logger.warning(f"连接失败: {host}:{port}")

                except Exception as e:
                    logger.error(f"连接服务器 {host}:{port} 时发生错误: {e}")
                    continue

            logger.error("所有通达信服务器连接失败")
            self._is_connected = False
            return False

        except Exception as e:
            logger.error(f"初始化通达信客户端失败: {e}")
            self._is_connected = False
            return False

    def _test_connection(self, api, host: str, port: int) -> bool:
        """
        测试通达信连接 (同步方法)

        Args:
            api: mootdx API实例
            host: 服务器地址
            port: 服务器端口

        Returns:
            连接是否成功
        """
        try:
            # 尝试连接
            api.connect(host, port)

            # 测试获取一些基本数据
            api.setup()

            # 断开测试连接
            return True

        except Exception as e:
            logger.debug(f"测试连接失败 {host}:{port}: {e}")
            return False

    async def _get_connection(self) -> Optional[Dict[str, Any]]:
        """
        从连接池获取可用连接

        Returns:
            可用的连接对象，如果没有则返回None
        """
        async with self._lock:
            # 查找可用的连接
            for conn in self._connection_pool:
                if not conn['in_use']:
                    conn['in_use'] = True
                    conn['last_used'] = datetime.now()
                    return conn

            # 如果没有可用连接，尝试创建新连接
            if len(self._connection_pool) < self.max_connections:
                try:
                    server = self._server_list[self._current_server_index]
                    api = get_api()

                    success = await asyncio.get_event_loop().run_in_executor(
                        self._executor, self._test_connection, api, server[0], server[1]
                    )

                    if success:
                        new_conn = {
                            'api': api,
                            'host': server[0],
                            'port': server[1],
                            'in_use': True,
                            'last_used': datetime.now()
                        }
                        self._connection_pool.append(new_conn)
                        return new_conn

                except Exception as e:
                    logger.error(f"创建新连接失败: {e}")

            return None

    async def _release_connection(self, connection: Dict[str, Any]):
        """
        释放连接回连接池

        Args:
            connection: 要释放的连接
        """
        async with self._lock:
            if connection in self._connection_pool:
                connection['in_use'] = False
                connection['last_used'] = datetime.now()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def get_tick_data(self, request: TickDataRequest) -> TickDataResponse:
        """
        获取单只股票分笔数据

        Args:
            request: 分笔数据查询请求

        Returns:
            分笔数据响应
        """
        if not self._is_connected:
            # 尝试重新连接
            if not await self.initialize():
                return TickDataResponse(
                    success=False,
                    message="通达信连接失败",
                    data=[]
                )

        connection = await self._get_connection()
        if not connection:
            return TickDataResponse(
                success=False,
                message="无可用连接",
                data=[]
            )

        try:
            # 确定市场代码
            market = MARKET_SH if request.market == "SH" else MARKET_SZ

            # 在线程池中执行同步的通达信API调用
            tick_data = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._fetch_tick_data_sync,
                connection['api'],
                request.stock_code,
                market,
                request.date
            )

            if tick_data:
                # 转换为内部格式
                converted_data = [
                    TickDataAdapter.from_tdx(tick, request.stock_code, request.date)
                    for tick in tick_data
                ]

                # 如果不包含集合竞价，则过滤掉09:25:00的数据
                if not request.include_auction:
                    converted_data = [
                        tick for tick in converted_data
                        if tick.time.time() != time(9, 25, 0)
                    ]

                # 按时间排序
                converted_data.sort(key=lambda x: x.time)

                return TickDataResponse(
                    success=True,
                    message=f"成功获取{request.stock_code}分笔数据",
                    data=converted_data,
                    summary={
                        "total_count": len(converted_data),
                        "date": request.date.date().isoformat(),
                        "include_auction": request.include_auction
                    }
                )
            else:
                return TickDataResponse(
                    success=False,
                    message=f"未获取到{request.stock_code}的分笔数据",
                    data=[]
                )

        except Exception as e:
            logger.error(f"获取{request.stock_code}分笔数据失败: {e}")
            return TickDataResponse(
                success=False,
                message=f"获取数据失败: {str(e)}",
                data=[]
            )
        finally:
            await self._release_connection(connection)

    def _fetch_tick_data_sync(self, api, stock_code: str, market: int, date: datetime) -> List[Dict[str, Any]]:
        """
        同步获取分笔数据

        Args:
            api: 通达信API实例
            stock_code: 股票代码
            market: 市场代码
            date: 查询日期

        Returns:
            分笔数据列表
        """
        try:
            # 重新连接以确保连接状态
            api.connect(self._server_list[self._current_server_index][0],
                       self._server_list[self._current_server_index][1])
            api.setup()

            # 获取分笔数据
            bars = api.bars(symbol=stock_code, market=market, date=date.strftime('%Y%m%d'))

            # 转换数据格式
            tick_data = []
            for bar in bars:
                # 通达信返回的字段可能需要调整，这里提供基本结构
                tick_data.append({
                    'time': bar.get('time', '09:30:00'),
                    'price': bar.get('price', 0),
                    'volume': bar.get('volume', 0),
                    'amount': bar.get('amount', 0),
                    'direction': bar.get('direction', 'N')
                })

            return tick_data

        except Exception as e:
            logger.error(f"同步获取分笔数据失败 {stock_code}: {e}")
            return []

    async def get_batch_tick_data(self, request: TickDataBatchRequest) -> TickDataBatchResponse:
        """
        批量获取分笔数据

        Args:
            request: 批量查询请求

        Returns:
            批量分笔数据响应
        """
        results = {}
        success_count = 0
        failed_stocks = []

        # 并发获取多只股票的数据
        semaphore = asyncio.Semaphore(self.max_connections)

        async def fetch_single_stock(stock_code: str) -> tuple[str, Optional[List[TickData]]]:
            async with semaphore:
                single_request = TickDataRequest(
                    stock_code=stock_code,
                    date=request.date,
                    market="SH" if stock_code.startswith(('60', '68', '90')) else "SZ",
                    include_auction=request.include_auction
                )

                response = await self.get_tick_data(single_request)
                if response.success and response.data:
                    return stock_code, response.data
                else:
                    return stock_code, None

        # 执行并发查询
        tasks = [fetch_single_stock(code) for code in request.stock_codes]
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        for task in completed_tasks:
            if isinstance(task, Exception):
                logger.error(f"批量查询异常: {task}")
                continue

            stock_code, data = task
            if data:
                results[stock_code] = data
                success_count += 1
            else:
                failed_stocks.append(stock_code)

        return TickDataBatchResponse(
            success=True,
            message=f"批量查询完成，成功{success_count}只，失败{len(failed_stocks)}只",
            data=results,
            success_count=success_count,
            failed_count=len(failed_stocks),
            failed_stocks=failed_stocks
        )

    async def get_status(self) -> DataSourceStatus:
        """
        获取数据源状态

        Returns:
            数据源状态信息
        """
        available_servers = []
        response_time = None
        error_message = None

        if self._is_connected:
            try:
                # 测试连接响应时间
                start_time = datetime.now()
                connection = await self._get_connection()

                if connection:
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds() * 1000
                    available_servers = [f"{conn['host']}:{conn['port']}"
                                       for conn in self._connection_pool
                                       if not conn['in_use']]
                    await self._release_connection(connection)
                else:
                    error_message = "无可用连接"

            except Exception as e:
                error_message = str(e)
                self._is_connected = False
        else:
            error_message = "未连接"

        return DataSourceStatus(
            source_name="通达信(TongDaXin)",
            is_connected=self._is_connected,
            last_check=datetime.now(),
            available_servers=available_servers,
            response_time=response_time,
            error_message=error_message
        )

    async def close(self):
        """关闭所有连接"""
        async with self._lock:
            for conn in self._connection_pool:
                try:
                    # 关闭通达信连接
                    if hasattr(conn['api'], 'close'):
                        await asyncio.get_event_loop().run_in_executor(
                            self._executor, conn['api'].close
                        )
                except Exception as e:
                    logger.warning(f"关闭连接时出错: {e}")

            self._connection_pool.clear()
            self._is_connected = False

        # 关闭线程池
        self._executor.shutdown(wait=True)
        logger.info("通达信客户端已关闭")


# 全局实例
tongdaxin_client = TongDaXinClient()