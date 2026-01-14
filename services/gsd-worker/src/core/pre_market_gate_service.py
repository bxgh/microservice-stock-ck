import logging
import asyncio
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any
import httpx
import os

from clickhouse_driver import Client
from core.clickhouse_client import ClickHouseClient
from core.notifier import Notifier

logger = logging.getLogger(__name__)

class PreMarketGateService:
    """
    盘前数据准备与校验服务 (Gate-1)
    
    职责:
    1. 校验昨日 K线覆盖率
    2. 校验昨日 分笔覆盖率
    3. 触发自动补采
    4. 发送状态报告
    """
    
    def __init__(self):
        self.ch_client = ClickHouseClient()
        self.notifier = Notifier()
        
        # 配置阈值 (可通过环境变量覆盖)
        self.kline_threshold = float(os.getenv("KLINE_THRESHOLD", "98.0"))
        self.tick_threshold = float(os.getenv("TICK_THRESHOLD", "95.0"))
        self.orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://127.0.0.1:18000")
        
    async def initialize(self):
        """初始化资源"""
        await self.ch_client.connect()
        logger.info("✅ ClickHouse 连接已建立")

    async def close(self):
        """释放资源"""
        self.ch_client.disconnect()
        logger.info("✅ ClickHouse 连接已关闭")

    async def run_gate_check(self) -> Dict[str, Any]:
        """执行 Gate-1 校验流程"""
        yesterday = self._get_yesterday_trading_date()
        logger.info(f"🛡️ 开始盘前校验, 目标日期: {yesterday}")
        
        # 1. 覆盖率检查
        kline_rate = await self._check_kline_coverage(yesterday)
        tick_rate = await self._check_tick_coverage(yesterday)
        
        logger.info(f"📊 校验结果: K线={kline_rate}%, 分笔={tick_rate}%")
        
        # 2. 判断是否补采
        # 只有确实低于阈值才触发，避免重复运行
        actions = []
        if kline_rate < self.kline_threshold:
            logger.warning(f"⚠️ K线覆盖率 {kline_rate}% < {self.kline_threshold}%, 触发补采")
            await self._trigger_recovery("daily_kline_sync", yesterday)
            actions.append("K线补采")
            
        if tick_rate < self.tick_threshold:
            logger.warning(f"⚠️ 分笔覆盖率 {tick_rate}% < {self.tick_threshold}%, 触发补采")
            await self._trigger_recovery("sync_tick", yesterday) # 注意: sync_tick 是任务名，需确认
            actions.append("分笔补采")
            
        # 3. 发送报告
        report = {
            "date": yesterday,
            "kline_rate": kline_rate,
            "tick_rate": tick_rate,
            "actions": actions,
            "status": "WARNING" if actions else "SUCCESS"
        }
        await self._send_report(report)
        return report

    def _get_yesterday_trading_date(self) -> str:
        """获取最近一个交易日 (简化版: 暂取昨天，后续对接交易日历)"""
        # TODO: 对接 baostock 或本地日历表获取准确的 T-1 交易日
        yesterday = datetime.now() - timedelta(days=1)
        # 如果是周六日，简单回推到周五 (仅作简单容错，最好查表)
        if yesterday.weekday() == 5: # Sat
            yesterday -= timedelta(days=1)
        elif yesterday.weekday() == 6: # Sun
            yesterday -= timedelta(days=2)
            
        return yesterday.strftime('%Y%m%d')

    async def _check_kline_coverage(self, date_str: str) -> float:
        """计算K线覆盖率"""
        query = f"""
        SELECT countDistinct(stock_code) 
        FROM stock_data.stock_kline_daily 
        WHERE trade_date = '{date_str}'
        """
        try:
            # ClickHouseClient 暂未封装 execute，直接用 internal client 或扩展
            # 这里假设 self.ch_client.execute 可用，如果不可用则需修改
            result = self.ch_client.client.execute(query)
            count = result[0][0]
            # 假设全市场约 5300 只
            rate = round(count / 5300 * 100, 2)
            return rate
        except Exception as e:
            logger.error(f"查询K线覆盖率失败: {e}")
            return 0.0

    async def _check_tick_coverage(self, date_str: str) -> float:
        """计算分笔覆盖率"""
        query = f"""
        SELECT countDistinct(stock_code) 
        FROM stock_data.tick_data 
        WHERE trade_date = '{date_str}'
        """
        try:
            result = self.ch_client.client.execute(query)
            count = result[0][0]
            rate = round(count / 5300 * 100, 2)
            return rate
        except Exception as e:
            logger.error(f"查询分笔覆盖率失败: {e}")
            return 0.0

    async def _trigger_recovery(self, task_id: str, date_str: str):
        """调用 Orchestrator 触发补采"""
        url = f"{self.orchestrator_url}/api/v1/tasks/{task_id}/trigger"
        # 暂时只支持 payload 传参，需确认 Orchestrator 是否已支持 params
        # 根据设计，我们计划扩展 /trigger 接口支持 params
        payload = {
            "params": {
                "target_date": date_str,
                "scope": "missing" # 补采模式
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info(f"✅ 成功触发任务 {task_id}")
                else:
                    logger.error(f"❌ 触发任务失败 {task_id}: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"❌ 触发任务异常 {task_id}: {e}")

    async def _send_report(self, report: Dict):
        """发送企微/钉钉报告"""
        icon = "✅" if report['status'] == "SUCCESS" else "⚠️"
        title = f"{icon} 盘前数据校验报告 ({report['date']})"
        
        content = [
            f"📅 对账日期: {report['date']}",
            f"📊 K线覆盖率: {report['kline_rate']}% " + ("(偏低)" if report['kline_rate'] < self.kline_threshold else ""),
            f"📊 分笔覆盖率: {report['tick_rate']}% " + ("(偏低)" if report['tick_rate'] < self.tick_threshold else ""),
        ]
        
        if report['actions']:
            content.append("⚡ 触发补采: " + ", ".join(report['actions']))
        else:
            content.append("✨ 数据就绪，无需补采")
            
        message = "\n".join(content)
        
        # 使用 Notifier 发送
        await self.notifier.send_alert(title, message)
