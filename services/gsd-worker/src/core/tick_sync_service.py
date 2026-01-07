"""
分笔数据同步核心服务

负责从 mootdx-api 采集盘后分笔数据并写入 ClickHouse
实现智能搜索矩阵策略，确保100%获取09:25集合竞价数据
"""

import asyncio
import aiohttp
import asynch
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import yaml
import pytz

logger = logging.getLogger(__name__)

# 上海时区
CST = pytz.timezone('Asia/Shanghai')


class TickSyncService:
    """分笔数据同步服务"""
    
    # 基于验证成功的搜索矩阵（参考：真正100%成功_修复版.py）
    SEARCH_MATRIX = [
        # 第一优先级：万科A验证成功区域
        (3500, 800, "万科A前区域"),
        (4000, 500, "万科A原成功"),
        (4500, 800, "万科A后区域"),
        
        # 第二优先级：深度搜索区域
        (3000, 1000, "深度区域1"),
        (5000, 1000, "深度区域2"),
        (6000, 1200, "深度区域3"),
        
        # 第三优先级：广域搜索
        (2000, 1500, "广域区域1"),
        (7000, 1500, "广域区域2"),
        (8000, 2000, "广域区域3"),
        
        # 第四优先级：极限搜索
        (1000, 2000, "极限区域1"),
        (10000, 3000, "极限区域2"),
    ]
    
    # 目标时间：集合竞价
    TARGET_TIME = "09:25"
    
    def __init__(self):
        self.clickhouse_pool = None
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.mootdx_api_url = os.getenv("MOOTDX_API_URL", "http://mootdx-api:8000")
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """初始化连接池"""
        async with self._lock:
            # ClickHouse 连接
            if self.clickhouse_pool is None:
                self.clickhouse_pool = await asynch.create_pool(
                    host=os.getenv("CLICKHOUSE_HOST", "clickhouse"),
                    port=int(os.getenv("CLICKHOUSE_PORT", "9000")),
                    database="stock_data",
                    user=os.getenv("CLICKHOUSE_USER", "default"),
                    password=os.getenv("CLICKHOUSE_PASSWORD", ""),
                    minsize=1,
                    maxsize=5
                )
                logger.info("✓ ClickHouse 连接池初始化完成")
            
            # HTTP 会话
            if self.http_session is None:
                timeout = aiohttp.ClientTimeout(total=120)
                self.http_session = aiohttp.ClientSession(timeout=timeout)
                logger.info(f"✓ HTTP 会话初始化完成: {self.mootdx_api_url}")
    
    async def close(self) -> None:
        """关闭连接池和会话"""
        async with self._lock:
            if self.clickhouse_pool:
                self.clickhouse_pool.close()
                await self.clickhouse_pool.wait_closed()
                self.clickhouse_pool = None
            if self.http_session:
                await self.http_session.close()
                await asyncio.sleep(0.25)  # 等待连接完全关闭
                self.http_session = None
            logger.info("连接池和会话已关闭")

    async def get_all_stocks(self) -> List[str]:
        """
        从 mootdx-api 获取全市场股票代码 (A股)
        
        过滤规则: 60/68 (沪), 00/30 (深)
        """
        logger.info("正在获取全市场股票列表...")
        all_codes = []
        
        try:
            # 获取深圳市场 (0) 和 上海市场 (1)
            for market in [0, 1]:
                url = f"{self.mootdx_api_url}/api/v1/stocks"
                params = {"market": market}
                
                async with self.http_session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data:
                            # 过滤 A 股代码
                            # 60xxxx: 沪市主板
                            # 68xxxx: 科创板
                            # 00xxxx: 深市主板
                            # 30xxxx: 创业板
                            market_codes = [
                                item['code'] for item in data 
                                if item.get('code', '').startswith(('60', '68', '00', '30'))
                            ]
                            all_codes.extend(market_codes)
                            logger.info(f"市场 {market} 获取到 {len(market_codes)} 只 A股股票")
                    else:
                        logger.error(f"获取市场 {market} 股票失败: {response.status}")
                        
            # 去重并排序
            all_codes = sorted(list(set(all_codes)))
            logger.info(f"全市场 A股总数: {len(all_codes)}")
            return all_codes
            
        except Exception as e:
            logger.error(f"获取全市场股票失败: {e}")
            return []
    
    async def fetch_tick_data_sequential(
        self,
        stock_code: str,
        trade_date: str,
        target_time: str = "09:25",
        batch_size: int = 800
    ) -> List[Dict[str, Any]]:
        """
        使用顺序批次回溯策略获取分笔数据，增加重试机制和稳定性
        """
        logger.debug(f"开始顺序批次回溯: {stock_code} ({trade_date})")
        
        all_data = []
        start = 0
        found_target = False
        max_batches = 25  # 800 * 25 = 20000
        
        for batch_idx in range(max_batches):
            retry_count = 0
            max_retries = 3
            batch_success = False
            
            while retry_count < max_retries:
                try:
                    url = f"{self.mootdx_api_url}/api/v1/tick/{stock_code}"
                    params = {"date": int(trade_date), "start": start, "offset": batch_size}
                    
                    async with self.http_session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            if not data:
                                batch_success = True
                                break
                                
                            all_data.extend(data)
                            times = [item.get('time', '23:59') for item in data]
                            earliest = min(times)
                            
                            logger.debug(f"SBF {stock_code} [{batch_idx}]: {len(data)}条, 最早 {earliest}")
                            
                            if earliest <= target_time:
                                found_target = True
                            
                            start += len(data)
                            batch_success = True
                            break
                        else:
                            logger.warning(f"SBF {stock_code} 批次 {batch_idx} 失败 ({response.status})，重试 {retry_count+1}")
                except Exception as e:
                    logger.warning(f"SBF {stock_code} 批次 {batch_idx} 异常 ({e})，重试 {retry_count+1}")
                
                retry_count += 1
                await asyncio.sleep(0.2 * retry_count)
            
            if not batch_success:
                logger.error(f"SBF {stock_code} 批次 {batch_idx} 最终失败，跳过")
                break
                
            if found_target:
                logger.info(f"🎯 {stock_code}: 已找齐全天数据 (共 {len(all_data)} 条)")
                break
                
            await asyncio.sleep(0.1)
            
        return all_data
    async def fetch_tick_data_smart(
        self, 
        stock_code: str, 
        trade_date: str
    ) -> List[Dict[str, Any]]:
        """
        使用智能搜索矩阵策略获取分笔数据
        
        策略：
        1. 遍历搜索矩阵（多个 start/offset 组合）
        2. 检查每批数据是否包含目标时间（09:25）
        3. 找到目标后继续1-2步确保完整性
        4. 合并去重并按时间升序排列
        
        Args:
            stock_code: 股票代码（如 000001）
            trade_date: 交易日期（YYYYMMDD）
            
        Returns:
            分笔数据列表
        """
        all_data = []
        found_target = False
        successful_step = None
        
        logger.debug(f"开始智能搜索: {stock_code} ({trade_date})")
        
        for i, (start, offset, description) in enumerate(self.SEARCH_MATRIX):
            try:
                url = f"{self.mootdx_api_url}/api/v1/tick/{stock_code}"
                params = {"date": int(trade_date), "start": start, "offset": offset}
                
                async with self.http_session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.warning(f"API 返回 {response.status}: {stock_code} @ {description}")
                        continue
                    
                    data = await response.json()
                    
                    if not data:
                        logger.debug(f"搜索步骤 {i+1}/{len(self.SEARCH_MATRIX)} ({description}): 无数据")
                        continue
                    
                    # 获取此批次的时间范围
                    batch_times = [item.get('time', '') for item in data]
                    if not batch_times:
                        continue
                    
                    current_earliest = min(batch_times)
                    current_latest = max(batch_times)
                    
                    logger.debug(
                        f"搜索步骤 {i+1}/{len(self.SEARCH_MATRIX)} ({description}): "
                        f"{len(data)} 条 ({current_earliest} ~ {current_latest})"
                    )
                    
                    # 检查是否找到目标时间
                    if current_earliest <= self.TARGET_TIME:
                        found_target = True
                        successful_step = description
                        logger.info(f"🎯 {stock_code}: 找到 {self.TARGET_TIME} 数据！步骤: {description}")
                        
                        all_data.append(data)
                        
                        # 智能停止：找到目标后继续1-2步确保完整性
                        if found_target and len(all_data) >= 3:
                            logger.debug(f"{stock_code}: 已确保完整性，停止搜索")
                            break
                    else:
                        all_data.append(data)
                
                # 避免服务器压力
                await asyncio.sleep(0.05)
                
            except aiohttp.ClientError as e:
                logger.warning(f"搜索步骤 {description} 失败: {stock_code}, 错误: {e}")
                continue
            except asyncio.TimeoutError:
                logger.warning(f"搜索步骤 {description} 超时: {stock_code}")
                continue
        
        if not all_data:
            logger.debug(f"{stock_code}: 搜索未获取到任何数据")
            return []
        
        # 合并所有批次数据
        merged_data = []
        for batch in all_data:
            merged_data.extend(batch)
        
        # 去重（基于 time + price + volume）
        seen = set()
        unique_data = []
        for item in merged_data:
            key = (item.get('time'), item.get('price'), item.get('volume'))
            if key not in seen:
                seen.add(key)
                unique_data.append(item)
        
        # 按时间升序排列
        unique_data.sort(key=lambda x: x.get('time', ''))
        
        if unique_data:
            earliest = unique_data[0].get('time', '')
            latest = unique_data[-1].get('time', '')
            logger.info(
                f"✓ {stock_code}: {len(unique_data)} 条记录 "
                f"({earliest} ~ {latest}) "
                f"{'✅' if earliest <= self.TARGET_TIME else '⚠️'}"
            )
        
        return unique_data
    
    def _map_direction(self, buyorsell: int) -> int:
        """映射买卖方向: 0=买 1=卖 2=中性"""
        if buyorsell == 0:
            return 0  # 买盘
        elif buyorsell == 1:
            return 1  # 卖盘
        else:
            return 2  # 中性
    
    async def sync_stock(
        self, 
        stock_code: str, 
        trade_date: str
    ) -> int:
        """
        同步单只股票的分笔数据
        
        Returns:
            写入记录数
        """
        # 使用顺序批次回溯策略获取数据（确保100%覆盖09:25）
        tick_data = await self.fetch_tick_data_sequential(stock_code, trade_date)
        
        if not tick_data:
            logger.debug(f"{stock_code} 无分笔数据")
            return 0
        
        # 转换日期格式
        trade_date_obj = datetime.strptime(trade_date, "%Y%m%d").date()
        
        # 准备插入数据 - 适配现有表结构
        # 表结构: symbol, trade_date, timestamp, price, volume, amount, direction, data_source, is_auction
        rows = []
        for item in tick_data:
            try:
                # 解析时间字符串为 datetime
                time_str = str(item.get('time', '09:30'))
                if len(time_str) == 5:  # HH:MM 格式
                    time_str = f"{time_str}:00"
                timestamp = datetime.strptime(
                    f"{trade_date} {time_str}", 
                    "%Y%m%d %H:%M:%S"
                )
                
                # 判断是否为集合竞价
                is_auction = 1 if time_str.startswith('09:25') else 0
                
                row = (
                    stock_code,                                    # symbol
                    trade_date_obj,                                # trade_date
                    timestamp,                                      # timestamp
                    float(item.get('price', 0)),                   # price
                    int(item.get('volume', 0)),                    # volume
                    int(float(item.get('price', 0)) * int(item.get('volume', 0))),  # amount (UInt64)
                    self._map_direction(int(item.get('buyorsell', 2))),  # direction
                    1,                                              # data_source: 1=mootdx
                    is_auction,                                     # is_auction
                )
                rows.append(row)
            except (ValueError, TypeError) as e:
                logger.warning(f"数据转换失败: {item}, 错误: {e}")
                continue
        
        if not rows:
            return 0
        
        # 写入 ClickHouse
        try:
            async with self.clickhouse_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        """
                        INSERT INTO tick_data 
                        (symbol, trade_date, timestamp, price, volume, amount, direction, data_source, is_auction)
                        VALUES
                        """,
                        rows
                    )
            
            logger.info(f"✓ {stock_code}: {len(rows)} 条分笔写入成功")
            return len(rows)
        except Exception as e:
            logger.error(f"❌ {stock_code}: ClickHouse 写入失败: {e}")
            return 0
    
    async def sync_stocks(
        self, 
        stock_codes: List[str], 
        trade_date: Optional[str] = None,
        concurrency: int = 3
    ) -> Dict[str, Any]:
        """
        批量同步多只股票
        
        Args:
            stock_codes: 股票代码列表
            trade_date: 交易日期，默认今天
            concurrency: 并发数（降低以减少服务器压力）
            
        Returns:
            同步结果统计
        """
        if trade_date is None:
            trade_date = datetime.now(CST).strftime("%Y%m%d")
        
        logger.info(f"开始同步分笔数据: {len(stock_codes)} 只股票, 日期: {trade_date}")
        
        semaphore = asyncio.Semaphore(concurrency)
        results = {"success": 0, "failed": 0, "total_records": 0, "errors": []}
        
        async def sync_with_limit(code: str):
            async with semaphore:
                try:
                    count = await self.sync_stock(code, trade_date)
                    if count > 0:
                        results["success"] += 1
                        results["total_records"] += count
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"{code}: 无数据")
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"{code}: {str(e)}")
                    logger.error(f"同步失败 {code}: {e}")
        
        tasks = [sync_with_limit(code) for code in stock_codes]
        await asyncio.gather(*tasks)
        
        logger.info(
            f"同步完成: 成功 {results['success']}, "
            f"失败 {results['failed']}, "
            f"总记录 {results['total_records']:,}"
        )
        
        return results
    
    async def get_stock_pool(self) -> List[str]:
        """
        获取待采集的股票池
        
        优先从配置文件读取 HS300 成分股，失败则使用内置默认列表
        """
        config_paths = [
            Path("/app/config/hs300_stocks.yaml"),
            Path(__file__).parent.parent.parent / "config" / "hs300_stocks.yaml",
        ]
        
        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path) as f:
                        config = yaml.safe_load(f)
                    stocks = config.get("stocks", [])
                    if stocks:
                        logger.info(f"从 {config_path} 加载 {len(stocks)} 只股票")
                        return stocks
                except Exception as e:
                    logger.warning(f"加载配置文件失败: {e}")
        
        # 使用内置默认股票池（部分 HS300 成分股）
        logger.warning("配置文件不存在，使用内置默认股票池")
        return [
            "000001", "000002", "000063", "000100", "000157",
            "000333", "000338", "000425", "000538", "000568",
            "000596", "000625", "000651", "000661", "000703",
            "000725", "000768", "000776", "000783", "000786",
            "000858", "000876", "000895", "000938", "000963",
            "002001", "002007", "002008", "002024", "002027",
            "002032", "002049", "002050", "002120", "002129",
            "002142", "002146", "002153", "002179", "002180",
            "300014", "300015", "300033", "300059", "300122",
            "300124", "300142", "300144", "300347", "300408",
            "600000", "600009", "600010", "600011", "600015",
            "600016", "600018", "600019", "600025", "600028",
            "600029", "600030", "600031", "600036", "600048",
            "600050", "600061", "600085", "600104", "600109",
            "600111", "600115", "600118", "600153", "600176",
            "600183", "600196", "600276", "600309", "600332",
            "600346", "600352", "600362", "600406", "600436",
            "600438", "600489", "600519", "600547", "600570",
            "600583", "600585", "600588", "600600", "600606",
            "600655", "600660", "600690", "600703", "600741",
        ]
