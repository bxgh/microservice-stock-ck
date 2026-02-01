import logging
import asyncio
from datetime import datetime, time, timedelta
from typing import Tuple, Dict, Any, List, Optional
import httpx
import os
import pytz
import json
import aiomysql
import redis.asyncio as redis
from redis.asyncio.cluster import RedisCluster, ClusterNode
import redis.asyncio as redis
from redis.asyncio.cluster import RedisCluster, ClusterNode
from gsd_shared.stock_universe import StockUniverseService
from gsd_shared.validation.standards import TickStandards
from gsd_shared.validation.market_validator import MarketValidator
import xxhash

from core.clickhouse_client import ClickHouseClient
from core.notifier import Notifier
from core.sync_status import SyncStatusTracker

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

# 常量定义
DEFAULT_KLINE_THRESHOLD = 98.0
DEFAULT_TICK_THRESHOLD = 95.0
DEFAULT_STOCK_COUNT_FALLBACK = 5360  # 沪深 A 股大约数量 (排除北交所)
STANDARD_TRADING_MINUTES = TickStandards.STANDARD_TRADING_MINUTES  # 241 分钟 (09:25-15:00)
HTTP_CLIENT_TIMEOUT_SECONDS = 10.0
DEFAULT_SHARD_REPAIR_THRESHOLD = 50.0

class PostMarketGateService:
    """
    盘后数据审计门禁 (Gate-3)
    
    职责:
    1. 校验当日 K线覆盖率
    2. 校验当日 分笔覆盖率
    3. 全量校验分笔时段完整性 (09:25-15:00)
    4. 校验收盘价对账一致性
    5. 结果持久化到云端 MySQL
    """
    
    def __init__(self):
        self.clickhouse_client = ClickHouseClient()
        self.notifier = Notifier()
        self.tracker = None
        self.market_validator = MarketValidator()
        self.lock = asyncio.Lock()
        
        # 配置阈值
        self.kline_threshold = float(os.getenv("KLINE_THRESHOLD", str(DEFAULT_KLINE_THRESHOLD)))
        self.tick_threshold = float(os.getenv("TICK_THRESHOLD", str(DEFAULT_TICK_THRESHOLD)))
        self.shard_repair_threshold = float(os.getenv("SHARD_REPAIR_THRESHOLD", str(DEFAULT_SHARD_REPAIR_THRESHOLD)))
        self.orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://127.0.0.1:18000")
        
        # 云端 MySQL 配置 (通过隧道)
        self.mysql_config = {
            "host": os.getenv("GSD_DB_HOST", "127.0.0.1"),
            "port": int(os.getenv("GSD_DB_PORT", 36301)), # SSH 隧道映射端口
            "user": os.getenv("GSD_DB_USER", "root"),
            "password": os.getenv("GSD_DB_PASSWORD", "alwaysup@888"),
            "db": os.getenv("GSD_DB_NAME", "alwaysup"),
            "autocommit": True
        }
        
        # Redis 配置
        self.redis_client = None
        self.redis_mode_is_cluster = os.getenv("REDIS_CLUSTER", "false").lower() == "true"
        self.redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_password = os.getenv("REDIS_PASSWORD", "redis123")
        self.redis_nodes = os.getenv("REDIS_NODES", "192.168.151.41:6379,192.168.151.58:6379,192.168.151.111:6379")
        
        # Stock Universe Service (Initialize in initialize())
        self.stock_universe = None
        
    async def initialize(self):
        """初始化资源"""
        await self.clickhouse_client.connect()
        
        # 初始化 Redis
        if self.redis_mode_is_cluster:
            nodes = [ClusterNode(h_p.split(':')[0], int(h_p.split(':')[1])) for h_p in self.redis_nodes.split(',')]
            self.redis_client = RedisCluster(startup_nodes=nodes, decode_responses=True, password=self.redis_password)
        else:
            self.redis_client = redis.Redis(host=self.redis_host, port=self.redis_port, password=self.redis_password, decode_responses=True)
            
        self.tracker = SyncStatusTracker(self.redis_client)
        
        # 初始化 StockService
        self.stock_universe = StockUniverseService(
            redis_client=self.redis_client,
            mysql_config=self.mysql_config,
            clickhouse_client=self.clickhouse_client.client
        )
        logger.info("✅ PostMarketGateService 初始化完成")

    async def close(self):
        """释放资源"""
        self.clickhouse_client.disconnect()
        if self.redis_client:
            await self.redis_client.aclose()
        logger.info("✅ 资源连接已释放")
    
    async def _get_all_stock_codes(self) -> List[str]:
        """[Deprecated] Use StockUniverseService instead"""
        return await self.stock_universe.get_all_a_stocks()
    
    def _get_target_trading_date(self) -> str:
        """
        获取目标交易日期
        规则：6:00 AM 之前返回前一日，之后返回当日
        
        Returns:
            日期字符串 (YYYY-MM-DD)
        """
        now = datetime.now(CST)
        
        # 如果当前时间在 6:00 AM 之前，使用前一天
        if now.hour < 6:
            target_date = now - timedelta(days=1)
            logger.info(f"⏰ 当前时间 {now.strftime('%H:%M')} < 06:00，使用前一交易日")
        else:
            target_date = now
        
        return target_date.strftime('%Y-%m-%d')

    def _normalize_date(self, date_str: str) -> str:
        """
        标准化日期格式为 YYYY-MM-DD
        支持 YYYYMMDD 和 YYYY-MM-DD
        """
        if not date_str:
            return self._get_target_trading_date()
        
        # 如果包含连字符，假设已经是 YYYY-MM-DD
        if '-' in date_str:
            return date_str
            
        # 尝试 YYYYMMDD 转换
        try:
            return datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
        except ValueError:
            logger.warning(f"无法识别的日期格式: {date_str}，尝试直接使用")
            return date_str

    async def run_gate_check(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """执行 Gate-3 审计流程"""
        today = self._normalize_date(date_str)
        logger.info(f"🛡️ 开始盘后深度审计, 目标日期: {today}")
        
        # 1. 基础覆盖率检查
        kline_rate = await self._check_kline_coverage(today)
        tick_rate = await self._check_tick_coverage(today)
        
        # 2. 深度质量检查 (全量时段完整性)
        continuity_summary = await self._check_all_ticks_continuity(today)
        
        # 3. 数据一致性检查 (抽样对账: 价格 + 成交量)
        consistency_report = await self._check_consistency(today)
        
        # 4. 判断是否需要补采
        actions = []
        if kline_rate < self.kline_threshold:
            logger.warning(f"⚠️ 当日 K线覆盖率 {kline_rate}% 不足")
            await self._trigger_recovery("repair_kline", today)
            actions.append("当日K线补采")
            
        # 4.2 分级补采逻辑
        # 只有在分片级别异常时才触发对应的修复策略
        # continuity_summary['failed_codes'] 包含了所有异常股票
        failed_codes = continuity_summary.get('failed_codes', [])
        
        # [SAFETY BRAKE] 极低覆盖率熔断机制
        # 如果覆盖率极低 (e.g. < 80%)，通常意味着系统性故障或当日休市，
        # 此时触发海量补采极易导致资源耗尽或误判。因此只记录审计失败，不自动触发修复。
        SAFETY_THRESHOLD = 80.0
        
        if tick_rate < SAFETY_THRESHOLD:
             logger.critical(f"⛔️ 覆盖率过低 ({tick_rate}% < {SAFETY_THRESHOLD}%)，触发安全熔断！")
             logger.critical("跳过自动补采，请人工介入排查是否为休市或全系统崩溃。")
             actions.append(f"安全熔断: 分笔覆盖率({tick_rate}%)过低，已跳过海量补采。请排查是否休市。")
        elif tick_rate < self.tick_threshold or len(failed_codes) > 0:
            logger.warning(f"⚠️ 当日分笔异常: 覆盖率={tick_rate}%, 异常股票数={len(failed_codes)}")
            # 按分片分组处理
            grouped_results = await self._process_tiered_repair(today, failed_codes)
            actions.extend(grouped_results)

        # 5. 生成报告并持久化
        status = "SUCCESS"
        if kline_rate < 90 or tick_rate < 90 or continuity_summary['failed_count'] > 500:
            status = "ERROR"
        elif actions:
            status = "WARNING"

        report = {
            "date": today,
            "gate_id": "GATE_3",
            "status": status,
            "kline_rate": kline_rate,
            "tick_rate": tick_rate,
            "metrics": {
                "continuity": continuity_summary,
                "consistency": consistency_report
            },
            "actions_taken": actions
        }
        
        # 持久化到云端
        await self._persist_to_cloud(report)
        
        # 发送企微报告
        await self._send_audit_report(report)
        return report

    async def _get_effective_stock_count(self) -> int:
        """获取有效的 A 股总数 (使用 StockUniverseService)"""
        try:
            # 优先从 Redis 全量获取
            codes = await self.stock_universe.get_all_a_stocks()
            if codes:
                return len(codes)
            
            return DEFAULT_STOCK_COUNT_FALLBACK
        except Exception as e:
            logger.warning(f"获取有效股票计数异常: {e}")
            return DEFAULT_STOCK_COUNT_FALLBACK

    async def _check_kline_coverage(self, date_str: str) -> float:
        """K线覆盖率: 对比本地 ClickHouse 与云端 MySQL 的记录数"""
        # 1. 获取有效 A 股总数
        total_stocks = await self._get_effective_stock_count()
        if total_stocks == 0:
            logger.warning(f"⚠️ 无法获取有效 A 股数量，无法计算 K线覆盖率")
            return 0.0
        
        # 2. 获取实际交易的股票数 (通过 StockUniverse)
        try:
            kline_stocks = await self.stock_universe.get_today_traded_stocks(date_str)
            clickhouse_count = len(kline_stocks)
            
            rate = round(clickhouse_count / total_stocks * 100, 2)
            logger.info(f"📊 K线覆盖率审计: ClickHouse={clickhouse_count}, Total_AShares={total_stocks}, Rate={rate}%")
            return rate
        except Exception as e:
            logger.error(f"❌ K线覆盖率检查失败: {e}")
            return 0.0

    # _get_mysql_kline_count removed as it is no longer used directly
    # logic moved to StockUniverseService if needed, or replaced by get_today_traded_stocks (source agnostic)

    async def _check_tick_coverage(self, date_str: str) -> float:
        """
        分笔覆盖率
        分子: 有 Tick 数据的股票数
        分母: 优先使用 K线数据股票数，但若 K线数据明显不足则降级使用全量股票数
        """
        # 确定表名: 如果是今天，使用 intraday 表
        is_today = date_str == datetime.now(CST).strftime('%Y-%m-%d')
        tick_table = "stock_data.tick_data_intraday" if is_today else "stock_data.tick_data"
        ds = date_str.replace('-', '')
        
        try:
            # 1. 获取实际交易的股票数 (作为 K线基准)
            # StockUniverse.get_today_traded_stocks 会优先查 CH Distributed，如果 CH 挂了会查 MySQL
            kline_stocks = await self.stock_universe.get_today_traded_stocks(date_str)
            total_kline = len(kline_stocks)
            
            # 2. 获取全市场有效 A 股总数 (作为备选分母)
            total_stocks = await self._get_effective_stock_count()
            
            # 3. 决定分母
            denominator = total_kline
            denominator_source = "K-Line (Ref)"
            
            if total_kline == 0:
                logger.warning(f"⚠️ 在 {date_str} 无 K线数据，降级使用股票总数")
                denominator = total_stocks
                denominator_source = "Stock List (Fallback)"
            elif total_kline < (total_stocks * 0.5):
                logger.warning(
                    f"⚠️ K线数据不足 ({total_kline} < {total_stocks * 0.5:.0f})，"
                    f"降级使用股票总数作为分母"
                )
                denominator = total_stocks
                denominator_source = "Stock List (Fallback)"
            
            if denominator == 0:
                logger.error("❌ 无法获取有效分母，无法计算分笔覆盖率")
                return 0.0
            
            # 4. 分子: 有 Tick 数据的股票数 (排除北证)
            tick_query = f"""
                SELECT countDistinct(stock_code) 
                FROM {tick_table} 
                WHERE trade_date = '{ds}'
                AND stock_code NOT LIKE '4%' 
                AND stock_code NOT LIKE '8%' 
                AND stock_code NOT LIKE '9%'
                AND stock_code NOT LIKE 'bj.%'
            """
            tick_result = self.clickhouse_client.client.execute(tick_query)
            total_tick = tick_result[0][0] if tick_result else 0
            
            # 5. 计算覆盖率
            rate = round(total_tick / denominator * 100, 2)
            logger.info(
                f"📊 分笔覆盖率: Tick={total_tick}, "
                f"Denominator={denominator} ({denominator_source}), Rate={rate}%"
            )
            return rate
        except Exception as e:
            logger.error(f"分笔覆盖率检查失败: {e}")
            return 0.0


    async def _check_all_ticks_continuity(self, date_str: str) -> Dict[str, Any]:
        """全量检查分笔时段完整性 (ClickHouse 分片聚合)"""
        is_today = date_str == datetime.now(CST).strftime('%Y-%m-%d')
        tick_table = "stock_data.tick_data_intraday" if is_today else "stock_data.tick_data"
        
        # 动态选择校验标准
        std = TickStandards.IntradayPostMarket if is_today else TickStandards.History
        
        min_active = std.MIN_ACTIVE_MINUTES
        min_time = std.MIN_TIME
        max_time = std.MAX_TIME

        # 1. 聚合查询统计每个股票的情况并返回异常代码
        query = f"""
        SELECT 
            stock_code,
            first_tick,
            last_tick,
            active_minutes
        FROM (
            SELECT 
                stock_code,
                min(tick_time) as first_tick,
                max(tick_time) as last_tick,
                countDistinct(toStartOfMinute(toDateTime(concat('2000-01-01 ', tick_time)))) as active_minutes
            FROM {tick_table} 
            WHERE trade_date = '{date_str.replace('-', '')}'
              AND stock_code NOT LIKE '4%'
              AND stock_code NOT LIKE '8%'
              AND stock_code NOT LIKE '9%'
              AND stock_code NOT LIKE 'bj.%'
            GROUP BY stock_code
        )
        WHERE active_minutes < {min_active} 
           OR first_tick > '{min_time}' 
           OR last_tick < '{max_time}'
        """
        try:
            res = self.clickhouse_client.client.execute(query)
            failed_codes = [row[0] for row in res]
            
            # 为了保持向前兼容，也统计计数
            insufficient = sum(1 for row in res if row[3] < min_active)
            late = sum(1 for row in res if row[1] > min_time)
            early = sum(1 for row in res if row[2] < max_time)
            
            # 获取当前节点覆盖到的有效 A 股总数 (排除北证)
            total_query = f"""
                SELECT countDistinct(stock_code) FROM {tick_table} 
                WHERE trade_date = '{date_str.replace('-', '')}'
                  AND stock_code NOT LIKE '4%'
                  AND stock_code NOT LIKE '8%'
                  AND stock_code NOT LIKE '9%'
                  AND stock_code NOT LIKE 'bj.%'
            """
            total_checked = self.clickhouse_client.client.execute(total_query)[0][0]

            return {
                "total_checked": total_checked,
                "insufficient_minutes_count": insufficient,
                "late_starts_count": late,
                "early_ends_count": early,
                "failed_count": len(failed_codes),
                "failed_codes": failed_codes
            }
        except Exception as e:
            logger.error(f"全量分笔连续性审计失败: {e}")
            return {"error": str(e), "failed_count": 0, "failed_codes": []}

    async def _process_tiered_repair(self, date_str: str, failed_codes: List[str]) -> List[str]:
        """
        [Refactored V4.0] 集中化修复逻辑 (Node 41 核心节点执行)
        
        策略:
        - 1-200 只: 集中定向补充 (stock_data_supplement)
        - > 200 只: 集中同步修复 (repair_tick)
        """
        actions = []
        failed_count = len(failed_codes)
        
        if failed_count == 0:
            logger.info("✅ 无异常股票，无需补采")
            return []

        logger.info(f"🔍 发现异常股票 {failed_count} 只，启动 Node 41 集中化自愈程序")
        
        if failed_count <= 200:
            logger.info(f"✅ 触发集中定向补充 (stock_data_supplement)")
            await self._trigger_targeted_supplement(date_str, failed_codes)
            actions.append(f"集中定向补充 ({failed_count}只)")
        else:
            logger.warning(f"🚨 异常数量过多 ({failed_count} 只)，触发集中同步修复 (repair_tick)")
            # 集中模式下 shard_id 设置为 None 或 0
            await self._trigger_shard_repair(date_str, None, failed_codes)
            actions.append(f"集中同步修复 ({failed_count}只)")
            
        return actions

    async def _trigger_shard_repair(self, date_str: str, shard_id: Optional[int], codes: Optional[List[str]]):
        """
        [Refactored V4.0] 发送集中修复指令到 MySQL
        """
        conn = None
        try:
            ds = date_str.replace('-', '')
            
            # 集中模式默认使用 shard_id=None 或针对核心节点参数
            params = {"date": ds}
            if shard_id is not None:
                params["shard_id"] = shard_id
            
            if codes:
                params["stock_codes"] = ",".join(codes)
            
            conn = await aiomysql.connect(**self.mysql_config)
            async with conn.cursor() as cur:
                # 去重检查
                check_sql = """
                    SELECT id, status FROM alwaysup.task_commands 
                    WHERE task_id = 'repair_tick' 
                      AND JSON_EXTRACT(params, '$.date') = %s 
                      AND created_at > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
                    ORDER BY id DESC LIMIT 1
                """
                await cur.execute(check_sql, (ds,))
                existing = await cur.fetchone()
                
                if existing:
                    logger.info(f"⏭️  跳过重复修复任务，已有任务 #{existing[0]}")
                    return
                
                # 插入新任务
                sql = "INSERT INTO alwaysup.task_commands (task_id, params, status) VALUES (%s, %s, %s)"
                await cur.execute(sql, ("repair_tick", json.dumps(params), "PENDING"))
            await conn.commit()
            logger.info(f"✅ 已插入集中式 repair_tick 指令: stocks={len(codes) if codes else 'all'}")
        except Exception as e:
            logger.error(f"❌ 插入集中修复指令失败: {e}")
        finally:
            if conn:
                conn.close()

    async def _get_shard_stocks_need_repair(self, date_str: str, shard_id: int, min_tick_count: int = 2000) -> List[str]:
        """
        查询指定分片中需要修复的股票列表
        
        Returns:
            需要修复的股票代码列表
        """
        try:
            # 1. 优先从当天K线数据获取股票列表（实际交易的股票）
            # trade_date 已经是 YYYY-MM-DD
            all_stocks = await self._get_stocks_from_kline(date_str)
            
            # 2. 降级逻辑：如果K线数据不可用，使用 stock_list
            if not all_stocks:
                logger.warning(f"⚠️ 无法从K线获取股票列表，降级到 stock_list")
                all_stocks = await self._get_all_stock_codes()
            
            # 3. 应用分片过滤
            shard_stocks = [
                code for code in all_stocks
                if xxhash.xxh64(code).intdigest() % 3 == shard_id
            ]
            
            if not shard_stocks:
                return []
            
            # 4. 批量查询质量状态
            # 动态选择表名 (Intraday vs History)
            is_today = date_str == datetime.now(CST).strftime('%Y-%m-%d')
            tick_table = "stock_data.tick_data_intraday" if is_today else "stock_data.tick_data"
            ds = date_str.replace('-', '') # ClickHouse Date usually accepts YYYY-MM-DD but string compare needs match if str. 
                                         # But here we pass '{trade_date}' in query. 
                                         # Using YYYY-MM-DD string with Date column works.
            
            codes_str = "','".join(shard_stocks)
            
            # 改用同步客户端执行
            query = f"""
                SELECT 
                    stock_code,
                    count() as tick_count,
                    min(tick_time) as min_time,
                    max(tick_time) as max_time
                FROM {tick_table}
                WHERE stock_code IN ('{codes_str}')
                  AND trade_date = '{date_str}' 
                GROUP BY stock_code
            """
            
            # 由于是同步调用，不需要 await (但放在 async 函数中 ok)
            rows = self.clickhouse_client.client.execute(query)
            
            # 5. 找出已达标的股票
            qualified = set()
            for row in rows:
                stock_code, tick_count, min_time, max_time = row
                if tick_count >= min_tick_count:
                    if min_time and max_time:
                        if min_time <= "10:00:00" and max_time >= "14:30:00":
                            qualified.add(stock_code)
                    else:
                        qualified.add(stock_code)
            
            # 6. 返回需要修复的（未采集 + 不达标）
            need_repair = [code for code in shard_stocks if code not in qualified]
            
            logger.info(
                f"Shard {shard_id}: {len(shard_stocks)} 只 → "
                f"已达标 {len(qualified)} 只, 需修复 {len(need_repair)} 只"
            )
            
            return need_repair
            
        except Exception as e:
            logger.error(f"查询 Shard {shard_id} 修复列表失败: {e}")
            return []  # 失败时返回空列表，避免触发不必要的修复

    async def _get_stocks_from_kline(self, trade_date: str) -> List[str]:
        """
        从当天K线数据获取实际交易的股票列表
        """
        return await self.stock_universe.get_today_traded_stocks(trade_date)

    async def _trigger_targeted_supplement(self, date_str: str, codes: List[str], shard_id: Optional[int] = None):
        """
        触发定向个股数据补充任务 (stock_data_supplement)
        
        Args:
            date_str: 交易日期 (YYYY-MM-DD)
            codes: 需要补充的股票代码列表
            shard_id: 可选，指定在哪个分片节点执行
        """
        conn = None
        try:
            ds = date_str.replace('-', '')
            
            # 构建任务参数
            params = {
                "stocks": codes,
                "date": ds,
                "data_types": ["tick"]
            }
            
            if shard_id is not None:
                params["shard_id"] = shard_id
            
            conn = await aiomysql.connect(**self.mysql_config)
            async with conn.cursor() as cur:
                # 去重检查
                stock_list = ",".join(sorted(codes))
                check_sql = """
                    SELECT id, status FROM alwaysup.task_commands 
                    WHERE task_id = 'stock_data_supplement' 
                      AND JSON_EXTRACT(params, '$.date') = %s
                      AND created_at > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
                    LIMIT 1
                """
                await cur.execute(check_sql, (ds,))
                existing = await cur.fetchone()
                
                if existing:
                    logger.info(f"⏭️  跳过重复补充任务: {len(codes)} 只股票, 已有任务 #{existing[0]}")
                    return
                
                # 插入新任务
                sql = "INSERT INTO alwaysup.task_commands (task_id, params, status) VALUES (%s, %s, %s)"
                await cur.execute(sql, ("stock_data_supplement", json.dumps(params), "PENDING"))
            await conn.commit()
            
            logger.info(f"✅ 已插入 stock_data_supplement 指令: {len(codes)} 只股票, shard_hint={shard_id}")
        except Exception as e:
            logger.error(f"❌ 插入定向补充指令失败: {e}")
        finally:
            if conn:
                conn.close()

    async def _check_consistency(self, date_str: str) -> Dict:
        """抽样对账 (价格 + 成交量)"""
        try:
            ds = date_str.replace('-', '')
            # 抽样 10 只
            stocks = ['600519', '000001', '601318', '000333', '600036', '000858', '600276', '601998', '000002', '300750']
            matches = 0
            is_today = date_str == datetime.now(CST).strftime('%Y-%m-%d')
            tick_table = "stock_data.tick_data_intraday" if is_today else "stock_data.tick_data"
            
            # 动态选择标准
            std = TickStandards.IntradayPostMarket if is_today else TickStandards.History
            price_tol = std.PRICE_TOLERANCE
            vol_tol = std.VOLUME_TOLERANCE
            
            for code in stocks:
                k_query = f"SELECT close_price, volume FROM stock_data.stock_kline_daily WHERE stock_code='{code}' AND trade_date='{ds}' LIMIT 1"
                t_query = f"SELECT argMax(price, tick_time), sum(volume) FROM {tick_table} WHERE stock_code='{code}' AND trade_date='{ds}'"
                
                k_res = self.clickhouse_client.client.execute(k_query)
                t_res = self.clickhouse_client.client.execute(t_query)
                
                if k_res and t_res:
                    # 1. 价格检查
                    price_ok = abs(float(k_res[0][0]) - float(t_res[0][0])) < price_tol
                    
                    # 2. 成交量检查
                    k_vol = float(k_res[0][1])
                    t_vol = float(t_res[0][1])
                    
                    if k_vol > 0:
                        vol_diff_ratio = abs(k_vol - t_vol) / k_vol
                        vol_ok = vol_diff_ratio < vol_tol
                    else:
                        vol_ok = (t_vol == 0)

                    if price_ok and vol_ok:
                        matches += 1
                        
            return {"sample_size": len(stocks), "matched": matches}
        except Exception as e:
            logger.error(f"一致性检查异常: {e}")
            return {"error": str(e)}

    async def _persist_to_cloud(self, report: Dict):
        """
        将审计结果持久化到腾讯云 MySQL (升级版 - 使用 AuditRepository)
        此方法现在会生成并保存全市场级别的校验结果。
        """
        try:
            # 1. 构造 ValidationResult 对象 (Market Level)
            from gsd_shared.validation.result import ValidationResult, ValidationIssue, ValidationLevel
            from gsd_shared.repository import AuditRepository
            
            # 使用现有连接池或临时创建连接池 (考虑到这里是单次调用，且 mysql_config 直接可用)
            # 注意: AuditRepository 需要 aiomysql.Pool，但这里我们只有一个 conn 配置
            # 为了简单起见，这里创建一个临时 pool
            async with aiomysql.create_pool(**self.mysql_config) as pool:
                repo = AuditRepository(pool)
                
                # 构造并填充 Result
                # 将字符串日期转为 datetime 以便设置 ValidationResult.timestamp
                try:
                    report_date = datetime.strptime(report['date'], '%Y-%m-%d')
                except ValueError:
                    # 如果还是失败（不应该，因为入口已经标准化了），尝试 YYYYMMDD
                    report_date = datetime.strptime(report['date'], '%Y%m%d')
                
                market_result = ValidationResult(
                    data_type="market",
                    target=report['date'],
                    timestamp=report_date,
                    # level 会根据 Issue 自动计算，或手动指定
                )
                
                # KLine Coverage Issue
                kline_level = ValidationLevel.PASS if report['kline_rate'] >= self.kline_threshold else ValidationLevel.WARN
                market_result.add_issue(ValidationIssue(
                    dimension="kline_coverage",
                    level=kline_level,
                    message=f"K线覆盖率: {report['kline_rate']}%",
                    context={"rate": report['kline_rate'], "threshold": self.kline_threshold}
                ))
                
                # Tick Coverage Issue
                tick_level = ValidationLevel.PASS if report['tick_rate'] >= self.tick_threshold else ValidationLevel.WARN
                market_result.add_issue(ValidationIssue(
                    dimension="tick_coverage",
                    level=tick_level,
                    message=f"分笔覆盖率: {report['tick_rate']}%",
                    context={"rate": report['tick_rate'], "threshold": self.tick_threshold}
                ))
                
                # Continuity Issue (Market Wide)
                cont_data = report['metrics']['continuity']
                failed_count = cont_data.get('failed_count', 0)
                if failed_count > 0:
                     market_result.add_issue(ValidationIssue(
                        dimension="market_continuity",
                        level=ValidationLevel.WARN, # 只要有失败的，全市场算 WARN? 或者根据阈值
                        message=f"发现 {failed_count} 只股票存在连续性问题",
                        context=cont_data
                    ))
                
                # [NEW] Persist Actions (e.g. Safety Brake)
                actions = report.get('actions_taken', [])
                for action in actions:
                    level = ValidationLevel.WARN
                    # 如果是熔断，升级为 FAIL
                    if "熔断" in action:
                        level = ValidationLevel.FAIL
                    
                    market_result.add_issue(ValidationIssue(
                        dimension="action_taken",
                        level=level,
                        message=action,
                        context={"action": action}
                    ))
                     
                # 保存到新表 (data_audit_summaries)
                success = await repo.save_result(market_result)
                
                if success:
                    logger.info(f"✅ 审计详情已通过 AuditRepository 保存 (ID: {market_result.target})")
                else:
                    logger.error("❌ AuditRepository 保存失败")

            # ------------------------------------------------------------------
            # (兼容旧逻辑) 为了保证 Gate Dashboard 不挂，保留对 old data_gate_audits 的写入
            # 待前端切换后再移除
            # ------------------------------------------------------------------
            is_complete = 1 if report['status'] == "SUCCESS" else 0
            # 构建简要说明
            m = report['metrics']['continuity']
            desc = f"K线覆盖率:{report['kline_rate']}% 分笔覆盖率:{report['tick_rate']}% 时段缺失:{m.get('failed_count', 0)}"
            
            conn = await aiomysql.connect(**self.mysql_config)
            async with conn.cursor() as cur:
                sql = """
                INSERT INTO alwaysup.data_gate_audits 
                (trade_date, gate_id, is_complete, description) 
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                is_complete=VALUES(is_complete), description=VALUES(description)
                """
                await cur.execute(sql, (
                    report['date'], 
                    report['gate_id'], 
                    is_complete,
                    desc
                ))
            await conn.ensure_closed()
            
        except Exception as e:
            logger.error(f"❌ 持久化审计结果失败: {e}")

    async def _trigger_recovery(self, task_id: str, date_str: str):
        """触发补采任务"""
        url = f"{self.orchestrator_url}/api/v1/tasks/{task_id}/trigger"
        payload = {"params": {"date": date_str.replace('-', '')}}
        try:
            async with httpx.AsyncClient(timeout=HTTP_CLIENT_TIMEOUT_SECONDS) as client:
                await client.post(url, json=payload)
        except: pass

    async def _send_audit_report(self, report: Dict):
        """发送企微审计报告"""
        m = report['metrics']['continuity']
        icon = "🛡️" if report['status'] == "SUCCESS" else ("🚨" if report['status'] == "ERROR" else "⚠️")
        title = f"{icon} 盘后审计报告 (Gate-3) - {report['date']}"
        
        content = [
            f"📅 交易日期: {report['date']}",
            f"📈 K线覆盖: {report['kline_rate']}%",
            f"📉 分笔覆盖: {report['tick_rate']}%",
            f"🕒 连续性审计 (全市场 {m.get('total_checked', 0)} 只):",
            f"  - 缺分钟数: {m.get('insufficient_minutes_count', 0)}",
            f"  - 晚开盘: {m.get('late_starts_count', 0)}",
            f"  - 早收盘: {m.get('early_ends_count', 0)}",
            f"💰 对账 (样): {report['metrics']['consistency'].get('matched', 0)}/{report['metrics']['consistency'].get('sample_size', 0)}",
        ]
        
        if report['actions_taken']:
            content.append(f"\n⚡ 响应动作: " + ", ".join(report['actions_taken']))
        else:
            content.append("\n✨ 今日数据质量完美，审计通过。")
            
        await self.notifier.send_alert(title, "\n".join(content))
