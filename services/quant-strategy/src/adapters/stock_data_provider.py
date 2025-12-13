from typing import List, Dict, Optional, Union, Any
import aiohttp
import pandas as pd
import logging
import json
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential
from config.settings import settings
from cache.redis_client import redis_client, CacheKeys, CacheTTL

logger = logging.getLogger(__name__)

class StockDataProvider:
    """
    数据适配层 (Adapter)
    
    负责与 get-stockdata 服务通信，获取行情和历史数据。
    实现自动重试、错误处理和数据验证。
    """
    
    def __init__(self):
        self.base_url = settings.stockdata_service_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=30)
        self._session: Optional[aiohttp.ClientSession] = None
        logger.info(f"StockDataProvider initialized with base URL: {self.base_url}")

    async def initialize(self) -> None:
        """初始化HTTP会话和Redis连接"""
        if not self._session:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
            logger.info("HTTP session created")
        
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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
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
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed for {url}: {e}")
            raise Exception(f"Failed to fetch data from {endpoint}: {e}")

    async def get_realtime_quotes(self, codes: List[str]) -> pd.DataFrame:
        """
        获取实时行情快照
        
        使用 /api/v1/datasources/test/{symbol} 端点获取实时数据
        
        Args:
            codes: 股票代码列表，如 ['600519', '000001']
            
        Returns:
            包含实时行情的DataFrame
        """
        if not codes:
            logger.warning("Empty codes list provided")
            return pd.DataFrame()
        
        logger.info(f"Fetching real-time quotes for {len(codes)} stocks")
        
        try:
            # 使用 /api/v1/datasources/test/{symbol} 端点
            # 这个端点测试数据源并返回实时数据
            results = []
            
            for code in codes:
                try:
                    # 1. Check cache first (cache-aside pattern)
                    cache_key = CacheKeys.quote(code)
                    cached_data = await redis_client.get(cache_key)
                    
                    if cached_data:
                        # Cache hit - parse JSON and use cached data
                        try:
                            cached_quote = json.loads(cached_data)
                            results.append(cached_quote)
                            continue
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid cached data for {code}, fetching fresh")
                    
                    # 2. Cache miss - fetch from API
                    data = await self._make_request('GET', f'/api/v1/datasources/test/{code}')
                    
                    # 3. Build result and cache it
                    if data and isinstance(data, dict):
                        quote_data = {
                            'code': code,
                            'name': data.get('name', ''),
                            'price': data.get('price', data.get('current', 0.0)),
                            'volume': data.get('volume', 0),
                            'change_pct': data.get('change_percent', data.get('change_pct', 0.0)),
                            'timestamp': datetime.now().isoformat()
                        }
                        results.append(quote_data)
                        
                        # Cache the result with TTL
                        try:
                            await redis_client.set(
                                cache_key, 
                                json.dumps(quote_data), 
                                ttl=CacheTTL.QUOTE
                            )
                        except Exception as cache_err:
                            logger.warning(f"Failed to cache quote for {code}: {cache_err}")
                    
                except Exception as e:
                    logger.warning(f"Failed to fetch quote for {code}: {e}")
                    continue
            
            df = pd.DataFrame(results)
            logger.info(f"Successfully fetched {len(df)} quotes")
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch real-time quotes: {e}")
            return pd.DataFrame()

    async def get_history_bar(
        self, 
        code: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        获取历史K线数据
        
        注意: 当前 get-stockdata 可能没有直接的 K线 API
        这里先返回空 DataFrame，待后续实现
        
        Args:
            code: 股票代码
            period: 时间周期 (1d, 5d, 1mo, 3mo, 6mo, 1y, etc.)
            interval: 数据间隔 (1m, 5m, 15m, 1h, 1d, etc.)
            
        Returns:
            包含K线数据的DataFrame
        """
        if not code:
            logger.warning("Empty stock code provided")
            return pd.DataFrame()
        
        logger.warning(f"Historical K-line API not yet implemented in get-stockdata for {code}")
        
        # TODO: 当 get-stockdata 实现 K线 API 后，更新此方法
        # 可能的端点: /api/v1/kline/{code} 或使用 fenbi 分笔数据聚合
        
        return pd.DataFrame()

    async def get_stock_info(self, code: str) -> Optional[Dict[str, Any]]:
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
            data = await self._make_request('GET', f'/api/v1/stocks/{code}/detail')
            
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

    async def search_stocks(self, query: str) -> List[Dict[str, Any]]:
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

    async def get_all_stocks(self, limit: int = 5000) -> List[Dict[str, Any]]:
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


# 全局单例
data_provider = StockDataProvider()

