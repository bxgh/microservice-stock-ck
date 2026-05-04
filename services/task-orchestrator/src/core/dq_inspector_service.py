import logging
import asyncio
import httpx
import docker
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import aiomysql
import os
import pytz

from core.dq import DQRule, DQSeverity, DQStatus, DQFinding, DQReport
from core.notifier import notifier
from config.settings import settings

logger = logging.getLogger(__name__)
TZ = pytz.timezone(settings.TIMEZONE)

class DQInspectorService:
    """
    数据质量巡检服务 (E3)
    
    职责:
    1. 基础设施自检 (Gost 隧道自愈)
    2. 数据完整性检查
    3. 连续性检查
    4. 停牌一致性检查
    5. 生成并持久化报告
    """
    
    def __init__(self):
        self.mysql_config = {
            "host": settings.MYSQL_HOST,
            "port": settings.MYSQL_PORT,
            "user": settings.MYSQL_USER,
            "password": settings.MYSQL_PASSWORD,
            "db": settings.MYSQL_DATABASE,
            "autocommit": True
        }
        try:
            self.docker_client = docker.DockerClient(base_url=settings.DOCKER_HOST)
        except Exception as e:
            logger.warning(f"⚠️ 无法初始化 Docker 客户端: {e}")
            self.docker_client = None

    async def pre_flight_check(self) -> bool:
        """
        [Phase 0] 基础设施自愈: 探测并恢复 Gost 隧道
        """
        logger.info("🛡️ 开始通道自检 (Pre-flight Check)...")
        
        # 1. 探测外网连通性 (尝试访问 Tushare)
        # 即使本地没有设置代理环境变量，我们也显式测试一下
        test_url = "https://api.tushare.pro"
        proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
        
        async with httpx.AsyncClient(proxy=proxy, timeout=5.0) as client:
            try:
                resp = await client.get(test_url)
                if resp.status_code == 200:
                    logger.info("✅ 外网通道正常 (Gost Active)")
                    return True
            except Exception as e:
                logger.error(f"❌ 外网通道中断: {e}")
        
        # 2. 如果失败，尝试重启 Gost 容器
        if self.docker_client:
            try:
                # 假设 gost 容器名为 'gost'
                container_name = os.getenv("GOST_CONTAINER_NAME", "gost")
                logger.info(f"🚀 正在尝试重启 {container_name} 容器...")
                container = self.docker_client.containers.get(container_name)
                container.restart()
                
                # 等待 10 秒让隧道重建
                await asyncio.sleep(10)
                
                # 再次探测
                async with httpx.AsyncClient(proxy=proxy, timeout=10.0) as client:
                    resp = await client.get(test_url)
                    if resp.status_code == 200:
                        logger.info("✨ Gost 通道恢复成功！")
                        await notifier.send_alert("基础设施自愈", "检测到 Gost 通道异常并已成功重启。", level="warning")
                        return True
            except Exception as restart_err:
                logger.error(f"🚨 Gost 重启失败: {restart_err}")
                await notifier.send_alert("基础设施故障", f"检测到 Gost 通道中断且尝试重启失败: {restart_err}", level="error")
        
        return False

    async def run_full_inspection(self, target_date: Optional[str] = None):
        """
        执行全量巡检任务
        """
        if not target_date:
            target_date = (datetime.now(TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
        
        logger.info(f"🔍 开始执行数据巡检任务, 目标日期: {target_date}")
        
        # 0. 通道自检
        await self.pre_flight_check()
        
        start_time = datetime.now(TZ)
        findings: List[DQFinding] = []
        
        # 1. 执行各类巡检逻辑
        try:
            async with aiomysql.connect(**self.mysql_config) as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    # 1.1 交易日判别
                    await cur.execute("SELECT is_open FROM trade_cal WHERE cal_date = %s", (target_date,))
                    row = await cur.fetchone()
                    if row and row['is_open'] == 0:
                        logger.info(f"☕ {target_date} 为非交易日，跳过数据巡检。")
                        return {"report": None, "status": "skipped_non_trading_day"}

                    # 1.2 完整性检查
                    findings.extend(await self.check_integrity(cur, target_date))
                    
                    # 1.3 停牌一致性检查
                    findings.extend(await self.check_suspension_consistency(cur, target_date))
                    
                    # 1.4 连续性检查 (检查过去 5 个交易日的断档)
                    findings.extend(await self.check_continuity(cur, target_date))
                    
                    # 1.5 持久化
                    # 计算得分 (简单模型)
                    score = max(0, 100 - len(findings) * 0.1)
                    end_time = datetime.now(TZ)
                    
                    report = DQReport(
                        inspection_date=target_date,
                        start_time=start_time,
                        end_time=end_time,
                        score=score,
                        summary={
                            "total_findings": len(findings),
                            "integrity_issues": len([f for f in findings if f.rule_id == DQRule.INTEGRITY]),
                            "continuity_issues": len([f for f in findings if f.rule_id == DQRule.CONTINUITY]),
                            "suspension_issues": len([f for f in findings if f.rule_id == DQRule.SUSPENSION]),
                        }
                    )
                    
                    await self._persist_results_with_cur(cur, findings, report)
                    await conn.commit()
                
        except Exception as e:
            logger.error(f"❌ 巡检逻辑执行失败: {e}")
            await notifier.send_alert("巡检任务异常", f"执行巡检任务时发生错误: {e}", level="error")
            return {"report": None, "error": str(e)}
        
        # 2. 发送通知
        await self._send_inspection_report(report)
        
        return {"report": report, "findings_count": len(findings)}

    async def check_integrity(self, cur, target_date: str) -> List[DQFinding]:
        """
        完整性检查: 应该有数据但实际缺失
        逻辑: 在股票池中且已上市未退市，非停牌日，但没有 K 线
        """
        logger.info(f"  [1/3] 正在执行完整性检查...")
        sql = """
        SELECT b.ts_code, b.name
        FROM stock_basic_info b
        LEFT JOIN stock_kline_daily k ON b.ts_code = k.ts_code AND k.trade_date = %s
        WHERE b.list_status = 'L' 
          AND b.list_date <= %s 
          AND (b.delist_date IS NULL OR b.delist_date > %s)
          AND k.ts_code IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM stock_suspensions s 
              WHERE s.ts_code = b.ts_code AND s.trade_date = %s AND s.is_suspended = 1
          )
        """
        await cur.execute(sql, (target_date, target_date, target_date, target_date))
        rows = await cur.fetchall()
        
        return [
            DQFinding(
                ts_code=row['ts_code'],
                trade_date=target_date,
                rule_id=DQRule.INTEGRITY,
                severity=DQSeverity.ERROR,
                description=f"数据缺失: {row['name']} ({row['ts_code']}) 在交易日 {target_date} 无 K 线记录且未标记停牌。"
            )
            for row in rows
        ]

    async def check_suspension_consistency(self, cur, target_date: str) -> List[DQFinding]:
        """
        停牌一致性检查: 标记停牌但有数据，或相反
        """
        logger.info(f"  [2/3] 正在执行停牌一致性检查...")
        findings = []
        
        # 情况 A: 标记停牌但有 K 线 (逻辑矛盾)
        sql_a = """
        SELECT s.ts_code, k.trade_date
        FROM stock_suspensions s
        JOIN stock_kline_daily k ON s.ts_code = k.ts_code AND s.trade_date = k.trade_date
        WHERE s.trade_date = %s AND s.is_suspended = 1
        """
        await cur.execute(sql_a, (target_date,))
        rows_a = await cur.fetchall()
        for row in rows_a:
            findings.append(DQFinding(
                ts_code=row['ts_code'],
                trade_date=target_date,
                rule_id=DQRule.SUSPENSION,
                severity=DQSeverity.WARN,
                description=f"停牌逻辑矛盾: {row['ts_code']} 在 {target_date} 标记为停牌但存在 K 线数据。"
            ))
            
        return findings

    async def check_continuity(self, cur, target_date: str) -> List[DQFinding]:
        """
        连续性检查: 寻找时间序列中的空洞
        逻辑: 检查过去 5 个交易日内，如果某股票有头有尾但中间断档
        """
        logger.info(f"  [3/3] 正在执行连续性检查...")
        # 1. 获取最近 5 个交易日
        await cur.execute("SELECT cal_date FROM trade_cal WHERE is_open = 1 AND cal_date <= %s ORDER BY cal_date DESC LIMIT 5", (target_date,))
        dates = [r['cal_date'].strftime('%Y-%m-%d') for r in await cur.fetchall()]
        if len(dates) < 2: return []
        
        start_date = dates[-1]
        end_date = dates[0]
        
        # 2. 传统 SQL 找断档 (适配 MySQL 5.7)
        # 逻辑：对于过去 5 个交易日中的每一天，检查是否有 K 线缺失
        sql = """
        SELECT b.ts_code, d.cal_date
        FROM stock_basic_info b
        CROSS JOIN (
            SELECT cal_date FROM trade_cal WHERE is_open = 1 AND cal_date BETWEEN %s AND %s
        ) d
        LEFT JOIN stock_kline_daily s ON b.ts_code = s.ts_code AND d.cal_date = s.trade_date
        WHERE b.list_status = 'L' AND b.list_date <= d.cal_date AND (b.delist_date IS NULL OR b.delist_date > d.cal_date)
          AND s.trade_date IS NULL
          AND NOT EXISTS (SELECT 1 FROM stock_suspensions susp WHERE susp.ts_code = b.ts_code AND susp.trade_date = d.cal_date AND susp.is_suspended = 1)
        LIMIT 500
        """
        await cur.execute(sql, (start_date, end_date))
        rows = await cur.fetchall()
        
        return [
            DQFinding(
                ts_code=row['ts_code'],
                trade_date=row['cal_date'].strftime('%Y-%m-%d'),
                rule_id=DQRule.CONTINUITY,
                severity=DQSeverity.WARN,
                description=f"序列断档: {row['ts_code']} 在历史序列 {row['cal_date']} 处缺失。"
            )
            for row in rows
        ]

    async def _persist_results_with_cur(self, cur, findings: List[DQFinding], report: DQReport):
        """
        使用现有游标保存结果
        """
        # 1. 保存报告
        report_sql = """
        INSERT INTO alwaysup.dq_reports (inspection_date, start_time, end_time, score, summary, status)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
        end_time=VALUES(end_time), score=VALUES(score), summary=VALUES(summary), status=VALUES(status)
        """
        import json
        await cur.execute(report_sql, (
            report.inspection_date,
            report.start_time,
            report.end_time,
            report.score,
            json.dumps(report.summary),
            report.status
        ))
        
        # 2. 保存发现的问题
        if findings:
            finding_sql = """
            INSERT INTO alwaysup.dq_findings (ts_code, trade_date, rule_id, severity, description, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            data = [
                (f.ts_code, f.trade_date, f.rule_id.value, f.severity.value, f.description, f.status.value)
                for f in findings
            ]
            await cur.executemany(finding_sql, data)
        
        logger.info(f"✅ 巡检结果已持久化 (ID: {report.inspection_date})")

    async def _persist_results(self, findings: List[DQFinding], report: DQReport):
        """
        保存结果到 MySQL (独立连接)
        """
        try:
            async with aiomysql.connect(**self.mysql_config) as conn:
                async with conn.cursor() as cur:
                    await self._persist_results_with_cur(cur, findings, report)
                    await conn.commit()
        except Exception as e:
            logger.error(f"❌ 巡检结果持久化失败: {e}")

    async def _send_inspection_report(self, report: DQReport):
        """
        发送巡检日报
        """
        icon = "🛡️" if report.score > 98 else ("⚠️" if report.score > 90 else "🚨")
        title = f"{icon} 数据质量巡检报告 - {report.inspection_date}"
        
        content = [
            f"📅 巡检日期: {report.inspection_date}",
            f"💯 质量得分: {report.score}",
            f"📊 异常概览:",
            f"  - 完整性异常: {report.summary.get('integrity_issues', 0)}",
            f"  - 连续性异常: {report.summary.get('continuity_issues', 0)}",
            f"  - 停牌逻辑异常: {report.summary.get('suspension_issues', 0)}",
            f"\n⏱ 执行耗时: {(report.end_time - report.start_time).seconds}s"
        ]
        
        await notifier.send_alert(title, "\n".join(content), level="info" if report.score > 95 else "warning")
