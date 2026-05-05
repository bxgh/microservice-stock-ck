import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Optional

import aiohttp
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential

from cache.redis_client import CacheKeys, CacheTTL, redis_client
from config.settings import settings
from domain.models.financial_models import FinancialIndicators

logger = logging.getLogger(__name__)

class StockDataProvider:
    """
    数据适配层 (Adapter)

    负责与 get-stockdata 服务通信，获取行情和历史数据。
    实现自动重试、错误处理和数据验证。
    """

    def __init__(self):
        self.base_url = settings.stockdata_service_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=2)
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()
        logger.info(f"StockDataProvider initialized with base URL: {self.base_url}")

    async def initialize(self) -> None:
        """初始化HTTP会话和Redis连接"""
        if self._session:
            return

        async with self._lock:
            if not self._session:
                # Disable trust_env to bypass environment proxies for local service calls
                self._session = aiohttp.ClientSession(
                    timeout=self.timeout,
                    trust_env=False
                )
                logger.info("HTTP session created (proxy-disabled)")

        # Initialize Redis cache
        try:
            await redis_client.initialize()
            logger.info("Redis cache initialized")
        except Exception as e:
            logger.warning(f"Redis cache initialization failed: {e}. Continuing without cache.")

    async def close(self) -> None:
        """关闭HTTP会话和Redis连接"""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("HTTP session closed")

        try:
            await redis_client.close()
            logger.info("Redis cache closed")
        except Exception as e:
            logger.warning(f"Redis close error: {e}")


    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json_data: dict | None = None
    ) -> dict[str, Any]:
        """
        统一的HTTP请求方法，带重试逻辑

        Args:
            method: HTTP方法 (GET, POST)
            endpoint: API端点 (不包含base_url)
            params: URL参数
            json_data: POST请求的JSON数据

        Returns:
            API响应的JSON数据

        Raises:
            Exception: 请求失败时抛出异常
        """
        if not self._session:
            await self.initialize()

        url = f"{self.base_url}{endpoint}"

        try:
            async with self._session.request(
                method,
                url,
                params=params,
                json=json_data
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

                # 检查get-stockdata的标准响应格式
                if isinstance(data, dict) and 'success' in data:
                    if not data.get('success'):
                        error_msg = data.get('message', 'Unknown error')
                        logger.error(f"API error: {error_msg}")
                        raise Exception(f"API returned error: {error_msg}")
                    return data.get('data', {})

                return data

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"HTTP request failed for {url}: {e}")
            raise Exception(f"Failed to fetch data from {endpoint}: {e}")

    async def get_realtime_quotes(self, codes: list[str]) -> pd.DataFrame:
        """
        获取实时行情快照 (Batch API)

        使用 /api/v1/quotes/realtime 批量端点获取实时数据
        提升效率，减少网络往返次数

        Args:
            codes: 股票代码列表，如 ['600519', '000001']

        Returns:
            包含实时行情的DataFrame
        """
        if not codes:
            logger.warning("Empty codes list provided")
            return pd.DataFrame()

        logger.info(f"Fetching real-time quotes for {len(codes)} stocks (batch mode)")

        try:
            # Strategy: Check cache first for all codes, then batch fetch cache misses
            cached_results = []
            uncached_codes = []

            # 1. Check cache for all codes
            for code in codes:
                cache_key = CacheKeys.quote(code)
                cached_data = await redis_client.get(cache_key)

                if cached_data:
                    try:
                        cached_quote = json.loads(cached_data)
                        cached_results.append(cached_quote)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid cached data for {code}, will fetch fresh")
                        uncached_codes.append(code)
                else:
                    uncached_codes.append(code)

            # 2. Batch fetch uncached quotes from API
            fresh_results = []
            if uncached_codes:
                logger.debug(f"Cache miss for {len(uncached_codes)} stocks, fetching from API")

                try:
                    # Use batch API: GET /api/v1/quotes/realtime?codes=600519,000001
                    codes_param = ','.join(uncached_codes)
                    batch_data = await self._make_request(
                        'GET',
                        '/api/v1/quotes/realtime',
                        params={'codes': codes_param}
                    )

                    # Parse batch response
                    if isinstance(batch_data, list):
                        quotes_list = batch_data
                    elif isinstance(batch_data, dict) and 'quotes' in batch_data:
                        quotes_list = batch_data['quotes']
                    else:
                        logger.warning(f"Unexpected batch response format: {type(batch_data)}")
                        quotes_list = []

                    # 3. Build results and cache each quote
                    for quote in quotes_list:
                        if not isinstance(quote, dict):
                            continue

                        code = quote.get('code', quote.get('stock_code', ''))
                        if not code:
                            continue

                        quote_data = {
                            'code': code,
                            'name': quote.get('name', quote.get('stock_name', '')),
                            'price': quote.get('price', quote.get('latest_price', quote.get('current', 0.0))),
                            'volume': quote.get('volume', 0),
                            'change_pct': quote.get('change_pct', quote.get('change_percent', 0.0)),
                            'timestamp': quote.get('timestamp', datetime.now().isoformat())
                        }
                        fresh_results.append(quote_data)

                        # Cache individual quote
                        try:
                            cache_key = CacheKeys.quote(code)
                            await redis_client.set(
                                cache_key,
                                json.dumps(quote_data),
                                ttl=CacheTTL.QUOTE
                            )
                        except Exception as cache_err:
                            logger.warning(f"Failed to cache quote for {code}: {cache_err}")

                except Exception as api_err:
                    logger.error(f"Batch API call failed: {api_err}. Falling back to single requests.")
                    # Fallback: Single requests for uncached codes
                    for code in uncached_codes:
                        try:
                            data = await self._make_request('GET', f'/api/v1/datasources/test/{code}')
                            if data and isinstance(data, dict):
                                quote_data = {
                                    'code': code,
                                    'name': data.get('name', ''),
                                    'price': data.get('price', data.get('current', 0.0)),
                                    'volume': data.get('volume', 0),
                                    'change_pct': data.get('change_percent', data.get('change_pct', 0.0)),
                                    'timestamp': datetime.now().isoformat()
                                }
                                fresh_results.append(quote_data)
                        except Exception as e:
                            logger.warning(f"Failed to fetch quote for {code}: {e}")

            # 4. Combine cached and fresh results
            all_results = cached_results + fresh_results
            df = pd.DataFrame(all_results)

            logger.info(f"Successfully fetched {len(df)} quotes (cached: {len(cached_results)}, fresh: {len(fresh_results)})")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch real-time quotes: {e}")
            return pd.DataFrame()

    async def get_history_bar(
        self,
        code: str,
        start_date: str | None = None,
        end_date: str | None = None,
        frequency: str = "d",
        adjust: str = "2"
    ) -> pd.DataFrame:
        """
        获取历史K线数据

        Args:
            code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            frequency: 频率: d=日, w=周, m=月, 1m, 5m, 15m, 30m, 60m
            adjust: 复权: 0=不复权, 1=前复权, 2=后复权

        Returns:
            包含K线数据的DataFrame
        """
        if not code:
            logger.warning("Empty stock code provided")
            return pd.DataFrame()

        params = {
            "start_date": start_date,
            "end_date": end_date,
            "frequency": frequency,
            "adjust": adjust
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}

        try:
            data = await self._make_request('GET', f'/api/v1/quotes/history/{code}', params=params)

            if isinstance(data, dict) and 'data' in data:
                df = pd.DataFrame(data['data'])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame()

            if not df.empty and 'code' in df.columns:
                df['code'] = df['code'].astype(str).str.zfill(6)

            return df
        except Exception as e:
            logger.error(f"Failed to fetch history bar for {code}: {e}")
            return pd.DataFrame()

    async def get_tick_data(self, code: str, date: str | None = None) -> pd.DataFrame:
        """
        获取分笔数据 (Tick Data)

        Args:
            code: 股票代码
            date: 日期 (YYYYMMDD)

        Returns:
            包含分笔数据的DataFrame
        """
        params = {"date": date} if date else {}
        try:
            data = await self._make_request('GET', f'/api/v1/quotes/tick/{code}', params=params)

            if isinstance(data, dict) and 'data' in data:
                df = pd.DataFrame(data['data'])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame()

            return df
        except Exception as e:
            logger.error(f"Failed to fetch tick data for {code}: {e}")
            return pd.DataFrame()

    async def get_market_ranking(self, ranking_type: str = "limit_up") -> pd.DataFrame:
        """
        获取市场榜单

        Args:
            ranking_type: limit_up, hot, up, volume
        """
        try:
            data = await self._make_request('GET', '/api/v1/market/ranking', params={"ranking_type": ranking_type})

            if isinstance(data, dict) and 'data' in data:
                df = pd.DataFrame(data['data'])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = pd.DataFrame()

            return df
        except Exception as e:
            logger.error(f"Failed to fetch market ranking {ranking_type}: {e}")
            return pd.DataFrame()

    async def get_sector_list(self) -> list[dict[str, Any]]:
        """获取板块列表"""
        try:
            data = await self._make_request('GET', '/api/v1/market/sector/list')
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to fetch sector list: {e}")
            return []

    async def get_sector_stocks(self, sector_code: str) -> list[dict[str, Any]]:
        """获取板块成分股"""
        try:
            data = await self._make_request('GET', f'/api/v1/market/sector/{sector_code}/stocks')
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to fetch sector stocks for {sector_code}: {e}")
            return []

    async def get_dragon_tiger_list(self, date: str | None = None) -> list[dict[str, Any]]:
        """获取龙虎榜数据"""
        params = {"date": date} if date else {}
        try:
            data = await self._make_request('GET', '/api/v1/market/dragon_tiger', params=params)
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to fetch dragon tiger list: {e}")
            return []

    async def get_capital_flow(self, code: str) -> dict[str, Any]:
        """获取个股资金流向"""
        try:
            data = await self._make_request('GET', f'/api/v1/market/capital_flow/{code}')
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.error(f"Failed to fetch capital flow for {code}: {e}")
            return {}

    async def get_stock_info(self, code: str) -> dict[str, Any] | None:
        """
        获取股票基本信息（带缓存）

        使用 /api/v1/stocks/{stock_code}/detail 端点

        Args:
            code: 股票代码

        Returns:
            股票信息字典
        """
        # 1. Check cache
        cache_key = CacheKeys.stock_info(code)
        cached_data = await redis_client.get(cache_key)

        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                logger.warning(f"Invalid cached stock info for {code}")

        # 2. Fetch from API
        try:
            data = await self._make_request('GET', f'/api/v1/stocks/{code}/info')

            # 3. Cache the result
            if data:
                try:
                    await redis_client.set(
                        cache_key,
                        json.dumps(data),
                        ttl=CacheTTL.STOCK_INFO
                    )
                except Exception as cache_err:
                    logger.warning(f"Failed to cache stock info for {code}: {cache_err}")

            return data
        except Exception as e:
            logger.error(f"Failed to fetch stock info for {code}: {e}")
            return None

    async def search_stocks(self, query: str) -> list[dict[str, Any]]:
        """
        搜索股票

        Args:
            query: 搜索关键词

        Returns:
            匹配的股票列表
        """
        try:
            data = await self._make_request('GET', f'/api/v1/stocks/search/{query}')
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Failed to search stocks for '{query}': {e}")
            return []

    async def get_all_stocks(self, limit: int = 5000) -> list[dict[str, Any]]:
        """
        获取全市场股票列表

        调用 get-stockdata 的 /api/v1/stocks/list 接口获取股票列表。
        结果缓存1小时。

        Args:
            limit: 返回数量限制，默认5000

        Returns:
            股票信息列表，每个元素包含 code, name, exchange 等字段
        """
        cache_key = f"stock_list:all:{limit}"

        # 1. 尝试从缓存获取
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.debug("Stock list cache hit")
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")

        # 2. 从 API 获取
        logger.info(f"Fetching all stocks from API (limit={limit})")

        try:
            # 使用 get-stockdata 的 /api/v1/stocks/list 端点
            data = await self._make_request(
                'GET',
                '/api/v1/stocks/list',
                params={'limit': limit}
            )

            # 处理响应格式
            if isinstance(data, list):
                stocks = data
            elif isinstance(data, dict):
                # 可能是分页响应
                stocks = data.get('data', data.get('stocks', []))
                if not isinstance(stocks, list):
                    stocks = []
            else:
                stocks = []

            logger.info(f"Fetched {len(stocks)} stocks from API")

            # 3. 缓存结果 (1小时)
            if stocks:
                try:
                    await redis_client.set(
                        cache_key,
                        json.dumps(stocks),
                        ttl=3600  # 1 hour
                    )
                except Exception as cache_err:
                    logger.warning(f"Failed to cache stock list: {cache_err}")

            return stocks

        except Exception as e:
            logger.error(f"Failed to fetch stock list: {e}")
            return []

    async def get_financial_indicators(self, code: str) -> Optional['FinancialIndicators']:
        """
        获取股票财务指标

        Args:
            code: 股票代码

        Returns:
            财务指标对象，如果获取失败返回None
        """
        from domain.models.financial_models import FinancialIndicators

        # akshare 需要 6 位数字代码
        code = code[:6] if isinstance(code, str) and len(code) >= 6 else code
        try:
            # Call the Verified Real API
            data = await self._make_request("GET", f"/api/v1/finance/indicators/{code}")

            if data:
                # Map fields to match FinancialIndicators model
                mapped_data = {
                    "stock_code": str(data.get("code", code)).zfill(6),
                    "report_date": data.get("report_date"),
                    "revenue": data.get("total_revenue", data.get("revenue")),
                    "net_profit": data.get("net_profit"),
                    "roe": data.get("roe"),
                    "net_assets": data.get("net_assets"),
                    "total_assets": data.get("total_assets"),
                    "goodwill": data.get("goodwill"),
                    "monetary_funds": data.get("monetary_funds"),
                    "interest_bearing_debt": data.get("interest_bearing_debt"),
                    "operating_cash_flow": data.get("operating_cash_flow") or data.get("net_cash_flow_from_operating_activities"),
                }
                return FinancialIndicators(**mapped_data)
            return None

        except Exception as e:
            logger.error(f"Failed to fetch real financial indicators for {code}: {repr(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    async def get_valuation(self, code: str) -> dict[str, Any] | None:
        """
        获取股票估值数据

        Args:
            code: 股票代码

        Returns:
            估值数据字典
        """
        # akshare 需要 6 位数字代码
        code = code[:6] if isinstance(code, str) and len(code) >= 6 else code
        try:
            # Call the Verified Real API
            data = await self._make_request("GET", f"/api/v1/market/valuation/{code}")
            if data and isinstance(data, dict):
                # Ensure code is string and mapped correctly
                if 'code' in data:
                    data['stock_code'] = str(data['code']).zfill(6)

                # Map pe/pb to pe_ttm/pb_ratio expected by ValuationService
                if 'pe' in data:
                    data['pe_ttm'] = data['pe']
                if 'pb' in data:
                    data['pb_ratio'] = data['pb']

                return data
            return None
        except Exception as e:
            logger.error(f"Failed to fetch valuation for {code}: {e}")
            return None

    async def get_industry_stats(self, industry_code: str) -> dict[str, Any] | None:
        """
        获取行业统计数据 (For Relative Scoring)

        Args:
            industry_code: 行业代码/名称 (如 "酿酒行业")

        Returns:
            行业统计数据字典 (包含 PE/PB/ROE/Growth 分布)
        """
        try:
            # Call Industry Stats API (corrected path)
            data = await self._make_request("GET", f"/api/v1/market/industry/{industry_code}/stats")
            return data
        except Exception as e:
            logger.warning(f"Failed to fetch industry stats for {industry_code}: {e}. Falling back to absolute scoring.")
            return None

    async def get_valuation_history(self, code: str, years: int = 5) -> dict[str, Any] | None:
        """
        获取历史估值数据 (For PE/PB Band Scoring)

        Args:
            code: 股票代码
            years: 历史年数

        Returns:
            包含 'stats', 'pe_ttm_list', 'pb_ratio_list' 的字典
        """
        try:
            # Call Real History API
            endpoint = f"/api/v1/market/valuation/{code}/history?years={years}&frequency=D"
            data = await self._make_request("GET", endpoint)

            # get-stockdata history response is {"code": "...", "data": [...], "count": ...}
            # ValuationService expects {"stats": {"pe_ttm": {...}, "pb_ratio": {...}}, ...}
            if data and isinstance(data, dict) and 'data' in data:
                history_list = data['data']
                stats = self._calculate_valuation_stats(history_list)
                data['stats'] = stats

            return data
        except Exception as e:
            logger.warning(f"Failed to fetch valuation history for {code}: {e}")
            return None

    def _calculate_valuation_stats(self, history_list: list[dict]) -> dict:
        """从历史记录计算统计信息 (min, max, median)"""
        import numpy as np

        pe_vals = [item.get('pe', item.get('pe_ttm')) for item in history_list if item.get('pe', item.get('pe_ttm')) is not None]
        pb_vals = [item.get('pb', item.get('pb_ratio')) for item in history_list if item.get('pb', item.get('pb_ratio')) is not None]

        def get_stats(vals):
            if not vals:
                return {}
            return {
                "min": float(np.min(vals)),
                "max": float(np.max(vals)),
                "median": float(np.median(vals)),
                "p25": float(np.percentile(vals, 25)),
                "p75": float(np.percentile(vals, 75))
            }

        return {
            "pe_ttm": get_stats(pe_vals),
            "pb_ratio": get_stats(pb_vals)
        }

# 全局单例
data_provider = StockDataProvider()
