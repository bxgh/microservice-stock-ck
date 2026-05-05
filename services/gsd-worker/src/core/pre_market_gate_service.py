import logging
import asyncio
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any, List
import httpx
import os
import pytz
import json
import aiomysql
from redis.asyncio import Redis
from redis.asyncio.cluster import RedisCluster

from core.clickhouse_client import ClickHouseClient
from core.notifier import Notifier

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

class PreMarketGateService:
    """
    盘前准入与名单校验服务 (Gate-1)
    
    职责:
    1. 校验全市场股票名单同步状态
    2. 校验 Redis 采集名单一致性
    3. 校验基础服务 (DB/Cache) 健康度
    4. 引用昨日 Gate-3 审计结果
    5. 结果持久化到云端 MySQL
    """
    
    def __init__(self):
        self.ch_client = ClickHouseClient()
        self.notifier = Notifier()
        self.redis = None
        
        # 配置
        self.orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://127.0.0.1:18000")
        self.cloud_api_url = os.getenv("CLOUD_API_URL", "http://124.221.80.250:8000/api/v1/stocks/all")
        self.proxy_url = os.getenv("HTTP_PROXY", "http://192.168.151.18:3128")
        
        # 云端 MySQL 配置 (通过隧道)
        self.mysql_config = {
            "host": os.getenv("GSD_DB_HOST", "127.0.0.1"),
            "port": int(os.getenv("GSD_DB_PORT", 36301)),
            "user": os.getenv("GSD_DB_USER", "root"),
            "password": os.getenv("GSD_DB_PASSWORD", "alwaysup@888"),
            "db": os.getenv("GSD_DB_NAME", "alwaysup"),
            "autocommit": True
        }

    async def initialize(self):
        """初始化资源"""
        await self.ch_client.connect()
        
        # 初始化 Redis
        redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_password = os.getenv("REDIS_PASSWORD", "redis123")
        is_cluster = os.getenv("REDIS_CLUSTER", "false").lower() == "true"
        
        url = f"redis://{redis_host}:{redis_port}"
        if is_cluster:
            self.redis = await RedisCluster.from_url(url, password=redis_password, decode_responses=True)
        else:
            self.redis = Redis.from_url(url, password=redis_password, decode_responses=True)
            
        logger.info("✅ PreMarketGateService 初始化完成")

    async def close(self):
        """释放资源"""
        self.ch_client.disconnect()
        if self.redis:
            await self.redis.aclose()
        logger.info("✅ 资源连接已释放")

    async def run_gate_check(self) -> Dict[str, Any]:
        """执行 Gate-1 校验流程"""
        now = datetime.now(CST)
        today = now.strftime('%Y-%m-%d')
        logger.info(f"🛡️ 开始盘前准入核查, 目标日期: {today}")
        
        # 1. 基础服务心跳检查
        db_ok = await self._check_db_heartbeat()
        redis_ok = await self._check_redis_heartbeat()
        
        # 2. 股票名单一致性检查
        list_sync_ok, list_desc = await self._check_stock_list_consistency()
        
        # 3. 昨日 Gate-3 状态核对 (仅参考)
        yesterday_gate_ok, gate_desc = await self._check_yesterday_gate_status(now)
        
        # 4. 校验当日表是否已清洗归档 (仅参考)
        migration_ok, migration_desc = await self._check_intraday_table_cleanliness(now)
        
        # 5. 判定整体状态 (Gate-1 核心标准: 仅关注名单与心跳)
        is_complete = 1 if (db_ok and redis_ok and list_sync_ok) else 0
        status = "SUCCESS" if is_complete else "WARNING"
        
        description = f"代码清单:{'OK' if list_sync_ok else 'FAIL'} 基础心跳:{'OK' if (db_ok and redis_ok) else 'FAIL'} (昨日审计:{'PASS' if yesterday_gate_ok else 'SKIP'} 归档清理:{'DONE' if migration_ok else 'PENDING'})"
        
        report = {
            "date": today,
            "gate_id": "GATE_1",
            "status": status,
            "is_complete": is_complete,
            "description": description,
            "details": {
                "db_heartbeat": db_ok,
                "redis_heartbeat": redis_ok,
                "list_consistency": list_sync_ok,
                "list_info": list_desc,
                "yesterday_gate": gate_desc,
                "table_cleanup": migration_desc
            }
        }
        
        # 5. 持久化到云端
        await self._persist_to_cloud(report)
        
        # 6. 发送告警报告
        await self._send_report(report)
        
        # 7. 自动触发修复 (名单若不一致，触发同步)
        if not list_sync_ok:
            logger.warning("🚨 检测到股票名单不一致，触发自动同步任务...")
            await self._trigger_task("daily_stock_collection", today)
            
        return report

    async def _check_db_heartbeat(self) -> bool:
        """检查 ClickHouse 连接"""
        try:
            self.ch_client.client.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"❌ DB 心跳异常: {e}")
            return False

    async def _check_redis_heartbeat(self) -> bool:
        """检查 Redis 连接"""
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"❌ Redis 心跳异常: {e}")
            return False

    async def _check_stock_list_consistency(self) -> Tuple[bool, str]:
        """检查股票名单一致性 (Cloud API vs Redis)"""
        try:
            # 1. 从云端获取计数
            params = {"security_type": "stock", "is_listed": "true", "is_active": "true"}
            async with httpx.AsyncClient(proxy=self.proxy_url, timeout=10.0) as client:
                resp = await client.get(self.cloud_api_url, params=params)
                if resp.status_code != 200:
                    return False, f"Cloud API 异常 ({resp.status_code})"
                cloud_total = resp.json().get("total", 0)
            
            # 2. 获取 Redis 计数
            redis_total = await self.redis.scard("metadata:stock_codes")
            
            # 3. 差异判定 (全量同步后，数量应完全对齐)
            actual_diff = abs(cloud_total - redis_total)
            
            if actual_diff > 10: # 允许少量浮动（如新股上市当天同步延迟）
                return False, f"名单不一致: 云端 {cloud_total}, 本地 {redis_total} (差值 {actual_diff})"
            
            return True, f"股票代码对齐 (全量: {redis_total})"
        except Exception as e:
            logger.error(f"❌ 名单校验异常: {e}")
            return False, str(e)

    async def _check_yesterday_gate_status(self, now_dt: datetime) -> Tuple[bool, str]:
        """核对昨日 Gate-3 状态"""
        yesterday_str = (now_dt - timedelta(days=1)).strftime('%Y-%m-%d')
        conn = None
        try:
            conn = await aiomysql.connect(**self.mysql_config)
            async with conn.cursor() as cur:
                sql = "SELECT is_complete FROM data_gate_audits WHERE trade_date=%s AND gate_id='GATE_3'"
                await cur.execute(sql, (yesterday_str,))
                row = await cur.fetchone()
                if row and row[0] == 1:
                    return True, "昨日审计通过"
                return False, "昨日审计未通过或无记录"
        except aiomysql.Error as e:
            logger.error(f"❌ 读取昨日状态数据库异常: {e}")
            return False, "数据库异常"
        except Exception as e:
            logger.error(f"❌ 读取昨日状态非预期异常: {e}")
            return False, "非预期异常"
        finally:
            if conn:
                conn.close()

    async def _check_intraday_table_cleanliness(self, now_dt: datetime) -> Tuple[bool, str]:
        """校验当日表是否已清洗（应不含今天之前的数据）"""
        today_str = now_dt.strftime('%Y-%m-%d')
        try:
            # 查询今日之前是否还有残留数据
            sql = f"SELECT count() FROM stock_data.tick_data_intraday WHERE trade_date < '{today_str}'"
            result = self.ch_client.execute(sql)
            stale_count = result[0][0]
            
            if stale_count > 0:
                return False, f"当日表未归档/清理: 发现 {stale_count} 条旧数据"
            
            return True, "当日表纯净 (已归档清理)"
        except Exception as e:
            logger.error(f"❌ 校验当日表清洗状态异常: {e}")
            return False, f"表核查异常: {str(e)}"

    async def _persist_to_cloud(self, report: Dict):
        """持久化审计结果到云端 (Gate-1)"""
        conn = None
        try:
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
                    report['is_complete'],
                    report['description']
                ))
            await conn.ensure_closed()
            logger.info(f"✅ 盘前审计结果已持久化 (is_complete={report['is_complete']})")
        except Exception as e:
            logger.error(f"❌ 持久化失败: {e}")
        finally:
            if conn:
                conn.close()

    async def _trigger_task(self, task_id: str, date_str: str):
        """触发任务"""
        url = f"{self.orchestrator_url}/api/v1/tasks/{task_id}/trigger"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, json={"params": {"date": date_str.replace('-', '')}})
        except Exception as e:
            logger.warning(f"触发任务 {task_id} 失败 (非阻塞): {e}")

    async def _send_report(self, report: Dict):
        """发送盘前准入报告"""
        icon = "🏁" if report['is_complete'] else "⚠️"
        title = f"{icon} 盘前准入报告 (Gate-1) - {report['date']}"
        
        content = [
            f"📅 对账日期: {report['date']}",
            f"📥 名单一致性: {'通过' if report['details']['list_consistency'] else '异常'}",
            f"  - {report['details']['list_info']}",
            f"💓 系统心跳: {'正常' if (report['details']['db_heartbeat'] and report['details']['redis_heartbeat']) else '检测到离线'}",
            f"🛡️ 昨日审计: {report['details']['yesterday_gate']}",
            f"\n📣 结论: {'准许开盘运行' if report['is_complete'] else '环境异常，请及时人工介入'}"
        ]
        
        await self.notifier.send_alert(title, "\n".join(content))
