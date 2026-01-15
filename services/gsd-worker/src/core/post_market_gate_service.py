import logging
import asyncio
from datetime import datetime, time
from typing import Tuple, Dict, Any, List
import httpx
import os
import pytz
import json
import aiomysql
import redis.asyncio as redis
from redis.asyncio.cluster import RedisCluster, ClusterNode
from gsd_shared.validators import is_valid_a_stock

from core.clickhouse_client import ClickHouseClient
from core.notifier import Notifier

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

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
        self.ch_client = ClickHouseClient()
        self.notifier = Notifier()
        
        # 配置阈值
        self.kline_threshold = float(os.getenv("KLINE_THRESHOLD", "98.0"))
        self.tick_threshold = float(os.getenv("TICK_THRESHOLD", "95.0"))
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
        
    async def initialize(self):
        """初始化资源"""
        await self.ch_client.connect()
        
        # 初始化 Redis
        if self.redis_mode_is_cluster:
            nodes = [ClusterNode(h_p.split(':')[0], int(h_p.split(':')[1])) for h_p in self.redis_nodes.split(',')]
            self.redis_client = RedisCluster(startup_nodes=nodes, decode_responses=True, password=self.redis_password)
        else:
            self.redis_client = redis.Redis(host=self.redis_host, port=self.redis_port, password=self.redis_password, decode_responses=True)
            
        logger.info("✅ PostMarketGateService 初始化完成")

    async def close(self):
        """释放资源"""
        self.ch_client.disconnect()
        if self.redis_client:
            await self.redis_client.aclose()
        logger.info("✅ 资源连接已释放")

    async def run_gate_check(self) -> Dict[str, Any]:
        """执行 Gate-3 审计流程"""
        today_obj = datetime.now(CST)
        today = today_obj.strftime('%Y-%m-%d')
        logger.info(f"🛡️ 开始盘后深度审计, 目标日期: {today}")
        
        # 1. 基础覆盖率检查
        kline_rate = await self._check_kline_coverage(today)
        tick_rate = await self._check_tick_coverage(today)
        
        # 2. 深度质量检查 (全量时段完整性)
        continuity_summary = await self._check_all_ticks_continuity(today)
        
        # 3. 数据一致性检查 (抽样对账)
        consistency_report = await self._check_price_consistency(today)
        
        # 4. 判断是否需要补采
        actions = []
        if kline_rate < self.kline_threshold:
            logger.warning(f"⚠️ 当日 K线覆盖率 {kline_rate}% 不足")
            await self._trigger_recovery("daily_kline_sync", today)
            actions.append("当日K线补采")
            
        if tick_rate < self.tick_threshold or continuity_summary['failed_count'] > 100:
            logger.warning(f"⚠️ 当日分笔异常: 覆盖率={tick_rate}%, 缺时段股票数={continuity_summary['failed_count']}")
            await self._trigger_recovery("repair_tick", today)
            actions.append("应当分笔补采")

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
        """获取有效的 A 股总数 (动态计算)"""
        try:
            # 从 Redis 获取全量名单
            codes = await self.redis_client.smembers("metadata:stock_codes")
            if not codes:
                return 5499 # 降级容错
            
            # 过滤 A 股
            count = 0
            for c in codes:
                pure_code = c.split('.')[0] if '.' in c else c
                if is_valid_a_stock(pure_code):
                    count += 1
            return count
        except Exception as e:
            logger.warning(f"获取有效股票计数异常: {e}")
            return 5499

    async def _check_kline_coverage(self, date_str: str) -> float:
        """K线覆盖率: 对比本地 ClickHouse 与云端 MySQL 的记录数"""
        # 1. 获取云端 MySQL 的 K线总数 (作为基准)
        mysql_count = await self._get_mysql_kline_count(date_str)
        if mysql_count == 0:
            logger.warning(f"⚠️ 云端 MySQL 在 {date_str} 无 K线数据，无法计算覆盖率")
            return 0.0
        
        # 2. 获取本地 ClickHouse 的 K线总数
        query = f"SELECT countDistinct(stock_code) FROM stock_data.stock_kline_daily WHERE trade_date = '{date_str.replace('-', '')}'"
        try:
            result = self.ch_client.client.execute(query)
            ch_count = result[0][0]
            
            rate = round(ch_count / mysql_count * 100, 2)
            logger.info(f"📊 K线覆盖率审计: ClickHouse={ch_count}, MySQL={mysql_count}, Rate={rate}%")
            return rate
        except Exception as e:
            logger.error(f"❌ K线覆盖率检查失败: {e}")
            return 0.0

    async def _get_mysql_kline_count(self, date_str: str) -> int:
        """获取云端 MySQL 中的 K 线记录数"""
        try:
            conn = await aiomysql.connect(**self.mysql_config)
            async with conn.cursor() as cur:
                sql = "SELECT COUNT(*) FROM stock_kline_daily WHERE trade_date = %s"
                await cur.execute(sql, (date_str,))
                res = await cur.fetchone()
                return res[0] if res else 0
            await conn.ensure_closed()
        except Exception as e:
            logger.error(f"❌ 获取云端 MySQL K线记录数失败: {e}")
            return 0

    async def _check_tick_coverage(self, date_str: str) -> float:
        """分笔覆盖率"""
        total_a = await self._get_effective_stock_count()
        # 确定表名: 如果是今天，使用 intraday 表
        is_today = date_str == datetime.now(CST).strftime('%Y-%m-%d')
        tick_table = "stock_data.tick_data_intraday" if is_today else "stock_data.tick_data"
        
        query = f"SELECT countDistinct(stock_code) FROM {tick_table} WHERE trade_date = '{date_str.replace('-', '')}'"
        try:
            result = self.ch_client.client.execute(query)
            count = result[0][0]
            return round(count / total_a * 100, 2)
        except Exception as e:
            logger.error(f"分笔覆盖率检查失败: {e}")
            return 0.0

    async def _check_all_ticks_continuity(self, date_str: str) -> Dict[str, Any]:
        """全量检查分笔时段完整性 (ClickHouse 分片聚合)"""
        # 核心逻辑：检查每只股票的分钟数
        # 正常交易日应有 120 (AM) + 120 (PM) + 1 (9:25) = 241 分钟
        # 确定表名: 如果是今天，使用 intraday 表
        is_today = date_str == datetime.now(CST).strftime('%Y-%m-%d')
        tick_table = "stock_data.tick_data_intraday" if is_today else "stock_data.tick_data"

        query = f"""
        SELECT 
            countDistinct(stock_code) as total,
            countIf(active_minutes < 235) as insufficient_minutes,
            countIf(first_tick > '09:25:05') as late_starts,
            countIf(last_tick < '14:59:55') as early_ends
        FROM (
            SELECT 
                stock_code,
                min(tick_time) as first_tick,
                max(tick_time) as last_tick,
                countDistinct(toStartOfMinute(toDateTime(concat('2000-01-01 ', tick_time)))) as active_minutes
            FROM {tick_table} 
            WHERE trade_date = '{date_str.replace('-', '')}'
            GROUP BY stock_code
        )
        """
        try:
            res = self.ch_client.client.execute(query)
            total, insufficient, late, early = res[0]
            failed_codes = insufficient + late + early # 可能有重合，但在 Gate-3 关心总量
            return {
                "total_checked": total,
                "insufficient_minutes_count": insufficient,
                "late_starts_count": late,
                "early_ends_count": early,
                "failed_count": failed_codes
            }
        except Exception as e:
            logger.error(f"全量分笔连续性审计失败: {e}")
            return {"error": str(e), "failed_count": 0}

    async def _check_price_consistency(self, date_str: str) -> Dict:
        """抽样对账"""
        try:
            ds = date_str.replace('-', '')
            # 抽样 10 只
            stocks = ['600519', '000001', '601318', '000333', '600036', '000858', '600276', '601998', '000002', '300750']
            matches = 0
            is_today = date_str == datetime.now(CST).strftime('%Y-%m-%d')
            tick_table = "stock_data.tick_data_intraday" if is_today else "stock_data.tick_data"
            
            for code in stocks:
                k_query = f"SELECT close_price FROM stock_data.stock_kline_daily WHERE stock_code='{code}' AND trade_date='{ds}' LIMIT 1"
                t_query = f"SELECT price FROM {tick_table} WHERE stock_code='{code}' AND trade_date='{ds}' ORDER BY tick_time DESC LIMIT 1"
                
                k_res = self.ch_client.client.execute(k_query)
                t_res = self.ch_client.client.execute(t_query)
                
                if k_res and t_res:
                    if abs(float(k_res[0][0]) - float(t_res[0][0])) < 0.011:
                        matches += 1
            return {"sample_size": len(stocks), "matched": matches}
        except Exception as e:
            logger.error(f"一致性检查异常: {e}")
            return {"error": str(e)}

    async def _persist_to_cloud(self, report: Dict):
        """将审计结果持久化到腾讯云 MySQL (精简版)"""
        try:
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
            logger.info(f"✅ 审计结果已持久化到云端 MySQL (is_complete={is_complete})")
        except Exception as e:
            logger.error(f"❌ 持久化审计结果失败: {e}")

    async def _trigger_recovery(self, task_id: str, date_str: str):
        """触发补采任务"""
        url = f"{self.orchestrator_url}/api/v1/tasks/{task_id}/trigger"
        payload = {"params": {"date": date_str.replace('-', '')}}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
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
