"""
数据质量检查服务

提供全市场和个股两个层面的数据质量检查：
- 全市场: 时效性、日完整性、唯一性、趋势稳定性
- 个股: 历史完整性、连续性、健康度评分
"""
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from data_access.mysql_pool import MySQLPoolManager

logger = logging.getLogger(__name__)


class DataQualityService:
    """数据质量检查服务"""
    
    def __init__(self):
        self.clickhouse_pool = None
        
    async def initialize(self):
        """初始化 ClickHouse 连接池"""
        import asynch
        import os
        
        ch_host = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
        ch_port = int(os.getenv('CLICKHOUSE_PORT', 9000))
        ch_user = os.getenv('CLICKHOUSE_USER', 'default')
        ch_password = os.getenv('CLICKHOUSE_PASSWORD', '')
        ch_database = os.getenv('CLICKHOUSE_DATABASE', 'stock_data')
        
        self.clickhouse_pool = await asynch.create_pool(
            host=ch_host,
            port=ch_port,
            user=ch_user,
            password=ch_password,
            database=ch_database,
            minsize=1,
            maxsize=3
        )
        logger.info("✓ DataQualityService 初始化完成")
        
    async def close(self):
        """关闭连接池"""
        if self.clickhouse_pool:
            self.clickhouse_pool.close()
            await self.clickhouse_pool.wait_closed()
            
    # ========== 全市场检查 ==========
    
    async def check_timeliness(self) -> Dict[str, Any]:
        """
        检查数据时效性
        
        Returns:
            {
                "latest_date": "2025-12-31",
                "lag_days": 0,
                "status": "OK" | "WARNING" | "ERROR",
                "message": "..."
            }
        """
        async with self.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        MAX(trade_date) as latest_date,
                        dateDiff('day', MAX(trade_date), today()) as lag_days
                    FROM stock_kline_daily
                """
                await cursor.execute(sql)
                result = await cursor.fetchone()
                
                latest_date = result[0]
                lag_days = result[1] if result[1] else 0
                
                # 判断状态 (考虑周末)
                today = datetime.now()
                is_weekend = today.weekday() >= 5
                
                if lag_days <= 1 or (is_weekend and lag_days <= 3):
                    status = "OK"
                    message = "数据时效正常"
                elif lag_days <= 3:
                    status = "WARNING"
                    message = f"数据滞后 {lag_days} 天"
                else:
                    status = "ERROR"
                    message = f"数据严重滞后 {lag_days} 天，请检查同步任务"
                    
                return {
                    "latest_date": str(latest_date) if latest_date else None,
                    "lag_days": lag_days,
                    "status": status,
                    "message": message,
                    "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
    
    async def check_daily_completeness(self, date: str = None) -> Dict[str, Any]:
        """
        检查指定日期的数据完整性
        
        Args:
            date: 检查日期，默认为最新交易日
            
        Returns:
            {
                "date": "2025-12-31",
                "expected": 5200,
                "actual": 5198,
                "missing_rate": "0.04%",
                "status": "OK" | "WARNING" | "ERROR",
                "missing_stocks": [...]
            }
        """
        async with self.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 获取检查日期
                if not date:
                    await cursor.execute("SELECT MAX(trade_date) FROM stock_kline_daily")
                    result = await cursor.fetchone()
                    date = str(result[0]) if result[0] else None
                    
                if not date:
                    return {"status": "ERROR", "message": "无数据可检查"}
                
                # 获取前一交易日作为基准
                sql_prev = """
                    SELECT MAX(trade_date) 
                    FROM stock_kline_daily 
                    WHERE trade_date < %(date)s
                """
                await cursor.execute(sql_prev, {"date": date})
                prev_result = await cursor.fetchone()
                prev_date = str(prev_result[0]) if prev_result[0] else None
                
                if not prev_date:
                    return {"status": "WARNING", "message": "无前一交易日数据作为基准"}
                
                # 对比两日数据
                sql_compare = """
                    SELECT 
                        (SELECT COUNT(DISTINCT stock_code) FROM stock_kline_daily WHERE trade_date = %(date)s) as actual,
                        (SELECT COUNT(DISTINCT stock_code) FROM stock_kline_daily WHERE trade_date = %(prev_date)s) as expected
                """
                await cursor.execute(sql_compare, {"date": date, "prev_date": prev_date})
                result = await cursor.fetchone()
                
                actual = result[0] or 0
                expected = result[1] or 0
                
                missing_rate = ((expected - actual) / expected * 100) if expected > 0 else 0
                
                # 判断状态
                if missing_rate <= 1:
                    status = "OK"
                    message = "数据完整性正常"
                elif missing_rate <= 5:
                    status = "WARNING"
                    message = f"缺失率 {missing_rate:.2f}%"
                else:
                    status = "ERROR"
                    message = f"数据大面积缺失 {missing_rate:.2f}%"
                
                # 获取缺失的股票列表 (最多返回 20 个)
                missing_stocks = []
                if actual < expected:
                    sql_missing = """
                        SELECT stock_code 
                        FROM stock_kline_daily 
                        WHERE trade_date = %(prev_date)s
                          AND stock_code NOT IN (
                              SELECT stock_code FROM stock_kline_daily WHERE trade_date = %(date)s
                          )
                        LIMIT 20
                    """
                    await cursor.execute(sql_missing, {"date": date, "prev_date": prev_date})
                    missing_stocks = [row[0] for row in await cursor.fetchall()]
                
                return {
                    "date": date,
                    "prev_date": prev_date,
                    "expected": expected,
                    "actual": actual,
                    "missing_count": expected - actual,
                    "missing_rate": f"{missing_rate:.2f}%",
                    "status": status,
                    "message": message,
                    "missing_stocks_sample": missing_stocks,
                    "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
    
    async def check_duplicates(self, days: int = 7) -> Dict[str, Any]:
        """
        检查最近 N 天的重复数据
        
        Returns:
            {
                "duplicate_count": 0,
                "duplicates": [...],
                "status": "OK" | "ERROR"
            }
        """
        async with self.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = """
                    SELECT stock_code, trade_date, COUNT(*) as cnt
                    FROM stock_kline_daily
                    WHERE trade_date >= today() - %(days)s
                    GROUP BY stock_code, trade_date
                    HAVING cnt > 1
                    ORDER BY cnt DESC
                    LIMIT 50
                """
                await cursor.execute(sql, {"days": days})
                results = await cursor.fetchall()
                
                duplicates = [
                    {"stock_code": r[0], "trade_date": str(r[1]), "count": r[2]}
                    for r in results
                ]
                
                status = "OK" if len(duplicates) == 0 else "ERROR"
                
                return {
                    "check_range_days": days,
                    "duplicate_count": len(duplicates),
                    "duplicates": duplicates,
                    "status": status,
                    "message": "无重复数据" if status == "OK" else f"发现 {len(duplicates)} 组重复数据",
                    "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
    
    async def check_trend_stability(self, weeks: int = 4) -> Dict[str, Any]:
        """
        检查周数据量趋势稳定性
        
        Returns:
            {
                "weeks": [...],
                "avg_count": 25000,
                "min_count": 24000,
                "max_count": 26000,
                "status": "OK" | "WARNING"
            }
        """
        async with self.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        toMonday(trade_date) as week_start,
                        COUNT(*) as record_count,
                        COUNT(DISTINCT stock_code) as stock_count
                    FROM stock_kline_daily
                    WHERE trade_date >= today() - %(days)s
                    GROUP BY week_start
                    ORDER BY week_start
                """
                await cursor.execute(sql, {"days": weeks * 7})
                results = await cursor.fetchall()
                
                weeks_data = [
                    {"week": str(r[0]), "records": r[1], "stocks": r[2]}
                    for r in results
                ]
                
                if not weeks_data:
                    return {"status": "WARNING", "message": "无足够数据进行趋势分析"}
                
                counts = [w["records"] for w in weeks_data]
                avg_count = sum(counts) / len(counts)
                min_count = min(counts)
                max_count = max(counts)
                
                # 检查波动率
                volatility = (max_count - min_count) / avg_count if avg_count > 0 else 0
                
                if volatility <= 0.2:
                    status = "OK"
                    message = "数据量趋势稳定"
                else:
                    status = "WARNING"
                    message = f"数据量波动较大 ({volatility*100:.1f}%)"
                
                return {
                    "weeks": weeks_data,
                    "avg_count": int(avg_count),
                    "min_count": min_count,
                    "max_count": max_count,
                    "volatility": f"{volatility*100:.1f}%",
                    "status": status,
                    "message": message,
                    "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
    
    # ========== 个股检查 ==========
    
    async def check_stock_completeness(self, stock_code: str) -> Dict[str, Any]:
        """
        检查单只股票的历史数据完整性
        
        Returns:
            {
                "stock_code": "sh.600519",
                "first_date": "2001-08-27",
                "last_date": "2025-12-31",
                "actual_count": 5732,
                "expected_count": 5800,
                "missing_count": 68,
                "missing_rate": "1.17%"
            }
        """
        async with self.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 获取该股票的数据范围
                sql_range = """
                    SELECT 
                        MIN(trade_date) as first_date,
                        MAX(trade_date) as last_date,
                        COUNT(*) as actual_count
                    FROM stock_kline_daily
                    WHERE stock_code = %(code)s
                """
                await cursor.execute(sql_range, {"code": stock_code})
                result = await cursor.fetchone()
                
                if not result[0]:
                    return {"status": "ERROR", "message": f"股票 {stock_code} 无数据"}
                
                first_date, last_date, actual_count = result
                
                # 计算该范围内应有的交易日数（用全市场数据估算）
                sql_expected = """
                    SELECT COUNT(DISTINCT trade_date) 
                    FROM stock_kline_daily
                    WHERE trade_date >= %(first)s AND trade_date <= %(last)s
                """
                await cursor.execute(sql_expected, {"first": first_date, "last": last_date})
                expected_result = await cursor.fetchone()
                expected_count = expected_result[0] if expected_result[0] else 0
                
                missing_count = max(0, expected_count - actual_count)
                missing_rate = (missing_count / expected_count * 100) if expected_count > 0 else 0
                
                # 判断状态
                if missing_rate <= 2:
                    status = "OK"
                elif missing_rate <= 10:
                    status = "WARNING"
                else:
                    status = "ERROR"
                
                return {
                    "stock_code": stock_code,
                    "first_date": str(first_date),
                    "last_date": str(last_date),
                    "actual_count": actual_count,
                    "expected_count": expected_count,
                    "missing_count": missing_count,
                    "missing_rate": f"{missing_rate:.2f}%",
                    "status": status,
                    "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
    
    async def check_stock_continuity(self, stock_code: str) -> Dict[str, Any]:
        """
        检查股票数据连续性，找出数据中断点
        
        Returns:
            {
                "stock_code": "sh.600519",
                "gaps": [
                    {"from": "2008-01-21", "to": "2008-02-15", "gap_days": 25}
                ]
            }
        """
        async with self.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        trade_date,
                        lagInFrame(trade_date, 1) OVER (ORDER BY trade_date) as prev_date
                    FROM stock_kline_daily
                    WHERE stock_code = %(code)s
                    ORDER BY trade_date
                """
                await cursor.execute(sql, {"code": stock_code})
                results = await cursor.fetchall()
                
                gaps = []
                for current_date, prev_date in results:
                    if prev_date:
                        gap_days = (current_date - prev_date).days
                        if gap_days > 10:  # 超过 10 天视为中断
                            gaps.append({
                                "from": str(prev_date),
                                "to": str(current_date),
                                "gap_days": gap_days
                            })
                
                status = "OK" if len(gaps) == 0 else "WARNING"
                
                return {
                    "stock_code": stock_code,
                    "gap_count": len(gaps),
                    "gaps": gaps[:20],  # 最多返回 20 个
                    "status": status,
                    "message": "数据连续" if status == "OK" else f"发现 {len(gaps)} 处数据中断",
                    "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
    
    async def calculate_health_score(self, stock_code: str) -> Dict[str, Any]:
        """
        计算股票数据健康度评分
        
        评分规则:
        - A: 完整性 > 95% 且 时效 <= 3 天
        - B: 完整性 > 80% 且 时效 <= 7 天
        - C: 其他
        """
        completeness = await self.check_stock_completeness(stock_code)
        continuity = await self.check_stock_continuity(stock_code)
        
        if completeness.get("status") == "ERROR":
            return {"stock_code": stock_code, "health_score": "N/A", "message": "无数据"}
        
        # 解析完整性
        missing_rate_str = completeness.get("missing_rate", "100%")
        missing_rate = float(missing_rate_str.replace("%", ""))
        completeness_rate = 100 - missing_rate
        
        # 解析时效性
        last_date = completeness.get("last_date")
        if last_date:
            last_dt = datetime.strptime(last_date, "%Y-%m-%d")
            freshness_days = (datetime.now() - last_dt).days
        else:
            freshness_days = 999
        
        # 计算评分
        if completeness_rate >= 95 and freshness_days <= 3:
            score = "A"
            message = "数据质量优秀"
        elif completeness_rate >= 80 and freshness_days <= 7:
            score = "B"
            message = "数据质量良好"
        else:
            score = "C"
            message = "数据质量需关注"
        
        return {
            "stock_code": stock_code,
            "health_score": score,
            "completeness_rate": f"{completeness_rate:.2f}%",
            "freshness_days": freshness_days,
            "gap_count": continuity.get("gap_count", 0),
            "message": message,
            "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    # ========== 综合报告与持久化 ==========
    
    async def _persist_report(self, report_dict: Dict[str, Any]):
        """
        将报告存入 MySQL 数据库
        """
        try:
            pool = await MySQLPoolManager.get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 1. 确保表存在
                    create_table_sql = """
                    CREATE TABLE IF NOT EXISTS data_quality_reports (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        report_type VARCHAR(20) NOT NULL,
                        overall_status VARCHAR(20) NOT NULL,
                        check_time DATETIME NOT NULL,
                        report_content JSON NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_report_type (report_type),
                        INDEX idx_check_time (check_time)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                    await cursor.execute(create_table_sql)
                    
                    # 2. 插入数据
                    insert_sql = """
                    INSERT INTO data_quality_reports 
                    (report_type, overall_status, check_time, report_content)
                    VALUES (%s, %s, %s, %s)
                    """
                    await cursor.execute(insert_sql, (
                        report_dict["report_type"],
                        report_dict["overall_status"],
                        report_dict["check_time"],
                        json.dumps(report_dict, ensure_ascii=False)
                    ))
                    
            logger.info(f"✓ {report_dict['report_type']} 质量报告已存入 MySQL")
        except Exception as e:
            logger.error(f"❌ 质量报告存入 MySQL 失败: {e}")
    
    async def run_daily_check(self) -> Dict[str, Any]:
        """
        执行每日质量检查（全市场）
        """
        logger.info("开始执行每日数据质量检查...")
        
        timeliness = await self.check_timeliness()
        completeness = await self.check_daily_completeness()
        duplicates = await self.check_duplicates()
        
        # 汇总状态
        all_status = [timeliness["status"], completeness["status"], duplicates["status"]]
        if "ERROR" in all_status:
            overall_status = "ERROR"
        elif "WARNING" in all_status:
            overall_status = "WARNING"
        else:
            overall_status = "OK"
        
        report = {
            "report_type": "daily",
            "overall_status": overall_status,
            "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "checks": {
                "timeliness": timeliness,
                "daily_completeness": completeness,
                "duplicates": duplicates
            }
        }
        
        # 持久化到 MySQL
        await self._persist_report(report)
        
        logger.info(f"每日质量检查完成: 整体状态 {overall_status}")
        return report
    
    async def run_weekly_check(self) -> Dict[str, Any]:
        """
        执行每周质量检查（含趋势分析）
        """
        logger.info("开始执行每周数据质量检查...")
        
        daily_report = await self.run_daily_check()
        trend = await self.check_trend_stability()
        
        daily_report["report_type"] = "weekly"
        daily_report["checks"]["trend_stability"] = trend
        
        # 更新整体状态
        if trend["status"] != "OK":
            if daily_report["overall_status"] == "OK":
                daily_report["overall_status"] = "WARNING"
        
        # 持久化到 MySQL (覆盖 daily 的持久化，因为这是更全的报告)
        await self._persist_report(daily_report)
        
        logger.info(f"每周质量检查完成: 整体状态 {daily_report['overall_status']}")
        return daily_report
