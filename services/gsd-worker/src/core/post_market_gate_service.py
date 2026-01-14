import logging
import asyncio
from datetime import datetime, time
from typing import Tuple, Dict, Any, List
import httpx
import os
import pytz

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
    3. 校验关键股票 (HS300) 的分笔完整性 (09:25-15:00)
    4. 校验收盘价对账一致性
    5. 触发补采并发送深度审计报告
    """
    
    def __init__(self):
        self.ch_client = ClickHouseClient()
        self.notifier = Notifier()
        
        # 配置阈值
        self.kline_threshold = float(os.getenv("KLINE_THRESHOLD", "98.0"))
        self.tick_threshold = float(os.getenv("TICK_THRESHOLD", "95.0"))
        self.orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://127.0.0.1:18000")
        self.strict_mode = os.getenv("STRICT_MODE", "true").lower() == "true"
        
    async def initialize(self):
        """初始化资源"""
        await self.ch_client.connect()
        logger.info("✅ PostMarketGateService 初始化完成")

    async def close(self):
        """释放资源"""
        self.ch_client.disconnect()
        logger.info("✅ ClickHouse 连接已关闭")

    async def run_gate_check(self) -> Dict[str, Any]:
        """执行 Gate-3 审计流程"""
        today = datetime.now(CST).strftime('%Y-%m-%d')
        logger.info(f"🛡️ 开始盘后深度审计, 目标日期: {today}")
        
        # 1. 基础覆盖率检查
        kline_rate = await self._check_kline_coverage(today)
        tick_rate = await self._check_tick_coverage(today)
        
        # 2. 深度质量检查 (时段完整性)
        continuity_report = []
        if self.strict_mode:
            continuity_report = await self._check_tick_continuity(today)
            
        # 3. 数据一致性检查 (对账)
        consistency_report = await self._check_price_consistency(today)
        
        # 4. 判断是否需要补采
        actions = []
        if kline_rate < self.kline_threshold:
            logger.warning(f"⚠️ 当日 K线覆盖率 {kline_rate}% 不足")
            await self._trigger_recovery("daily_kline_sync", today)
            actions.append("当日K线补采")
            
        if tick_rate < self.tick_threshold:
            logger.warning(f"⚠️ 当日 分笔覆盖率 {tick_rate}% 不足")
            # 注意: 这里触发分片补采或者全量补采取决于策略
            # 简化版触发一次全量补采
            await self._trigger_recovery("repair_tick", today)
            actions.append("应当分笔补采")

        # 5. 生成综合报告
        report = {
            "date": today,
            "kline_rate": kline_rate,
            "tick_rate": tick_rate,
            "continuity": continuity_report,
            "consistency": consistency_report,
            "actions": actions,
            "status": "ERROR" if (kline_rate < 90 or tick_rate < 90) else ("WARNING" if actions else "SUCCESS")
        }
        
        await self._send_audit_report(report)
        return report

    async def _check_kline_coverage(self, date_str: str) -> float:
        """K线覆盖率"""
        query = f"SELECT countDistinct(stock_code) FROM stock_data.stock_kline_daily WHERE trade_date = '{date_str}'"
        try:
            result = self.ch_client.client.execute(query)
            count = result[0][0]
            return round(count / 5350 * 100, 2)
        except Exception as e:
            logger.error(f"K线覆盖率检查失败: {e}")
            return 0.0

    async def _check_tick_coverage(self, date_str: str) -> float:
        """分笔覆盖率"""
        query = f"SELECT countDistinct(stock_code) FROM stock_data.tick_data WHERE trade_date = '{date_str}'"
        try:
            result = self.ch_client.client.execute(query)
            count = result[0][0]
            return round(count / 5350 * 100, 2)
        except Exception as e:
            logger.error(f"分笔覆盖率检查失败: {e}")
            return 0.0

    async def _check_tick_continuity(self, date_str: str) -> List[Dict]:
        """检查核心股票的时段覆盖情况 (抽样 HS300)"""
        # 抽取若干代表性股票检查
        samples = ['000001', '600036', '600519', '000333', '601318']
        report = []
        
        for code in samples:
            query = f"""
            SELECT 
                min(tick_time) as first_tick,
                max(tick_time) as last_tick,
                count() as total_count
            FROM stock_data.tick_data 
            WHERE stock_code = '{code}' AND trade_date = '{date_str}'
            """
            try:
                res = self.ch_client.client.execute(query)
                first, last, count = res[0]
                
                # 情况判定
                has_0925 = first <= "09:25:01" if first else False
                has_1500 = last >= "15:00:00" if last else False
                
                status = "OK"
                if not has_0925 or not has_1500 or count < 1000:
                    status = "MISSING_PERIODS"
                
                report.append({
                    "code": code,
                    "first": str(first),
                    "last": str(last),
                    "count": count,
                    "status": status
                })
            except Exception as e:
                logger.error(f"检查连续性失败 {code}: {e}")
        return report

    async def _check_price_consistency(self, date_str: str) -> Dict:
        """收盘价一致性检查 (抽样)"""
        query = f"""
        WITH 
          (SELECT stock_code, close FROM stock_data.stock_kline_daily WHERE trade_date = '{date_str}' LIMIT 10) as klines,
          (SELECT stock_code, last_value(price) as last_tick_price FROM stock_data.tick_data WHERE trade_date = '{date_str}' GROUP BY stock_code LIMIT 10) as ticks
        SELECT klines.stock_code, klines.close, ticks.last_tick_price
        FROM klines INNER JOIN ticks ON klines.stock_code = ticks.stock_code
        """
        # 注意: 这里的 SQL 可能需要根据实际 ClickHouse 架构调整 (分布式表下的 argMax/last_value)
        # 为简化，我们执行两次查询手动对比
        try:
            # 抽样 5 只
            stocks = ['600519', '000001', '601318']
            matches = 0
            for code in stocks:
                k_query = f"SELECT close FROM stock_data.stock_kline_daily WHERE stock_code='{code}' AND trade_date='{date_str}' LIMIT 1"
                t_query = f"SELECT price FROM stock_data.tick_data WHERE stock_code='{code}' AND trade_date='{date_str}' ORDER BY tick_time DESC LIMIT 1"
                
                k_res = self.ch_client.client.execute(k_query)
                t_res = self.ch_client.client.execute(t_query)
                
                if k_res and t_res:
                    if abs(k_res[0][0] - t_res[0][0]) < 0.01:
                        matches += 1
            return {"sample_size": len(stocks), "matched": matches}
        except Exception as e:
            logger.error(f"一致性对账失败: {e}")
            return {"error": str(e)}

    async def _trigger_recovery(self, task_id: str, date_str: str):
        """触发 Orchestrator 任务"""
        url = f"{self.orchestrator_url}/api/v1/tasks/{task_id}/trigger"
        payload = {"params": {"date": date_str.replace('-', '')}}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, json=payload)
        except Exception as e:
            logger.error(f"触发补采失败: {e}")

    async def _send_audit_report(self, report: Dict):
        """发送 Gate-3 深度审计报告"""
        icon = "🛡️" if report['status'] == "SUCCESS" else "⚠️"
        title = f"{icon} 盘后数据深度审计 (Gate-3) - {report['date']}"
        
        content = [
            f"📅 审计日期: {report['date']}",
            f"📈 K线覆盖: {report['kline_rate']}%",
            f"📉 分笔覆盖: {report['tick_rate']}%",
        ]
        
        # 连续性抽样
        if report['continuity']:
            content.append("\n🕒 时段连续性抽样:")
            for item in report['continuity']:
                mark = "✅" if item['status'] == "OK" else "❌"
                content.append(f"  {mark} {item['code']}: {item['first']} -> {item['last']} ({item['count']}条)")
        
        # 对账抽样
        if 'consistency' in report and 'matched' in report['consistency']:
            c = report['consistency']
            content.append(f"\n💰 收盘价对账: {c['matched']}/{c['sample_size']} 匹配")

        if report['actions']:
            content.append(f"\n⚡ 响应动作: " + ", ".join(report['actions']))
        else:
            content.append("\n✨ 今日数据质量完美，审计通过。")
            
        await self.notifier.send_alert(title, "\n".join(content))
