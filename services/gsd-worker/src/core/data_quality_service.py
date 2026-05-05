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
from config.settings import settings

logger = logging.getLogger(__name__)


class DataQualityService:
    """数据质量检查服务"""
    
    def __init__(self):
        self.clickhouse_pool = None
        self._benchmark_cache = {}  # (start_date, end_date) -> [dates]
        
    async def initialize(self):
        """初始化 ClickHouse 连接池"""
        import asynch
        import os
        
        ch_host = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
        ch_port = int(os.getenv('CLICKHOUSE_PORT', 9000))
        ch_user = os.getenv('CLICKHOUSE_USER', 'default')
        ch_password = os.getenv('CLICKHOUSE_PASSWORD', '')
        ch_database = os.getenv('CLICKHOUSE_DATABASE', 'stock_data')
        
        self.clickhouse_pool = await asyncio.wait_for(
            asynch.create_pool(
                host=ch_host,
                port=ch_port,
                user=ch_user,
                password=ch_password,
                database=ch_database,
                minsize=1,
                maxsize=3,
                connect_timeout=settings.db_connect_timeout,
                send_receive_timeout=settings.db_io_timeout,
                sync_request_timeout=settings.db_io_timeout
            ),
            timeout=settings.db_connect_timeout + settings.db_connect_timeout_buffer
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
    
    async def check_cross_db_consistency(self, days: int = 7) -> Dict[str, Any]:
        """
        [对账逻辑] 检查最近 N 天 MySQL 与 ClickHouse 的记录数一致性
        这是判断同步质量的最直接标准。
        
        Returns:
            {
                "status": "OK" | "ERROR",
                "details": [
                    {"date": "2025-12-31", "mysql_count": 5468, "clickhouse_count": 5468, "diff": 0, "status": "OK"},
                    ...
                ]
            }
        """
        # 1. 获取 MySQL 统计
        mysql_stats = {}
        try:
            pool = await MySQLPoolManager.get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    sql = """
                        SELECT trade_date, COUNT(*) as cnt 
                        FROM stock_kline_daily 
                        WHERE trade_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                        GROUP BY trade_date
                        ORDER BY trade_date DESC
                    """
                    await cursor.execute(sql, (days,))
                    for date, count in await cursor.fetchall():
                        mysql_stats[str(date)] = count
        except Exception as e:
            logger.error(f"MySQL 统计查询失败: {e}")
            return {"status": "ERROR", "message": f"MySQL 查询异常: {e}"}

        # 2. 获取 ClickHouse 统计
        ch_stats = {}
        try:
            async with self.clickhouse_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    sql = """
                        SELECT trade_date, count(*) as cnt 
                        FROM stock_kline_daily 
                        WHERE trade_date >= today() - %(days)s
                        GROUP BY trade_date
                        ORDER BY trade_date DESC
                    """
                    await cursor.execute(sql, {"days": days})
                    for date, count in await cursor.fetchall():
                        ch_stats[str(date)] = count
        except Exception as e:
            logger.error(f"ClickHouse 统计查询失败: {e}")
            return {"status": "ERROR", "message": f"ClickHouse 查询异常: {e}"}

        # 3. 对比分析
        details = []
        is_all_ok = True
        
        # 以 MySQL 的日期为准（源头）
        for date, m_count in mysql_stats.items():
            c_count = ch_stats.get(date, 0)
            diff = m_count - c_count
            status = "OK" if diff == 0 else "ERROR"
            if diff != 0:
                is_all_ok = False
            
            details.append({
                "date": date,
                "mysql_count": m_count,
                "clickhouse_count": c_count,
                "diff": diff,
                "status": status
            })

        overall_status = "OK" if is_all_ok and details else "ERROR"
        message = "源数据库与 ClickHouse 数据完全对齐" if overall_status == "OK" else "发现源数据库与 ClickHouse 存在数据不一致"
        if not details:
            overall_status = "WARNING"
            message = "最近 7 天范围内无数据可对比"

        return {
            "status": overall_status,
            "message": message,
            "days": days,
            "details": details,
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

    # ========== 深度扫描 (Universe Deep Scan) ==========
    
    async def _get_benchmark_calendar(self, start_date: str, end_date: str, cursor) -> List[str]:
        """
        获取基准日历 (以 sh.000001 为准)
        """
        cache_key = (start_date, end_date)
        if cache_key in self._benchmark_cache:
            return self._benchmark_cache[cache_key]

        # 优先使用 sh.000001，如果由于某种原因不可用，则使用全市场合集
        sql = """
            SELECT DISTINCT trade_date 
            FROM stock_kline_daily 
            WHERE stock_code = 'sh.000001'
              AND trade_date >= %(start)s AND trade_date <= %(end)s
            ORDER BY trade_date
        """
        await cursor.execute(sql, {"start": start_date, "end": end_date})
        results = await cursor.fetchall()
        
        # 如果 000001 没数据，退而求其次使用市场最活跃的日期集合（去重后的合集）
        if not results:
            sql_fallback = """
                SELECT DISTINCT trade_date 
                FROM stock_kline_daily 
                WHERE trade_date >= %(start)s AND trade_date <= %(end)s
                ORDER BY trade_date
            """
            await cursor.execute(sql_fallback, {"start": start_date, "end": end_date})
            results = await cursor.fetchall()
        
        final_dates = [str(r[0]) for r in results]
        self._benchmark_cache[cache_key] = final_dates
        return final_dates

    async def _is_market_suspended(self, date: str, cursor) -> bool:
        """
        探测某天是否全市场停牌（通过全市场活跃度判断）
        """
        await cursor.execute(
            "SELECT COUNT(*) FROM stock_kline_daily WHERE trade_date = %(date)s",
            {"date": date}
        )
        count = (await cursor.fetchone())[0]
        # 如果全市场只有不到 10 只股票有数据，判定为非交易日
        return count < 10

    async def check_stock_health_deep(self, stock_code: str) -> Dict[str, Any]:
        """
        执行个股精准深度扫描 (零容忍模式)
        """
        async with self.clickhouse_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 1. 获取个股数据范围
                await cursor.execute(
                    "SELECT MIN(trade_date), MAX(trade_date) FROM stock_kline_daily WHERE stock_code = %(code)s",
                    {"code": stock_code}
                )
                res = await cursor.fetchone()
                if not res or not res[0]:
                    return {"stock_code": stock_code, "status": "ERROR", "message": "无历史记录"}
                
                start_date, end_date = str(res[0]), str(res[1])
                
                # 2. 获取基准日历
                benchmark = await self._get_benchmark_calendar(start_date, end_date, cursor)
                
                # 3. 获取个股实际日历
                await cursor.execute(
                    "SELECT trade_date FROM stock_kline_daily WHERE stock_code = %(code)s ORDER BY trade_date",
                    {"code": stock_code}
                )
                actual = [str(r[0]) for r in await cursor.fetchall()]
                
                # 4. 计算差集 (缺失日期)
                missing_dates = list(set(benchmark) - set(actual))
                missing_dates.sort()
                
                # 5. 过滤停牌 (Batch Optimized)
                true_missing = []
                suspensions = []
                
                if missing_dates:
                    # 一次性查询所有缺失日期的市场活跃度
                    await cursor.execute(
                        "SELECT trade_date, COUNT(*) FROM stock_kline_daily WHERE trade_date IN %(dates)s GROUP BY trade_date",
                        {"dates": missing_dates}
                    )
                    market_activity = {str(r[0]): r[1] for r in await cursor.fetchall()}
                    
                    for m_date in missing_dates:
                        market_count = market_activity.get(m_date, 0)
                        if market_count > 100:
                            true_missing.append(m_date)
                        else:
                            suspensions.append(m_date)
                
                # 6. 判定状态 (零容忍：缺一天即 ERROR)
                status = "OK" if not true_missing else "ERROR"
                
                report = {
                    "stock_code": stock_code,
                    "status": status,
                    "listing_date": start_date,
                    "last_date": end_date,
                    "missing_count": len(true_missing),
                    "missing_dates": true_missing,
                    "suspension_count": len(suspensions),
                    "check_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                return report

    async def _persist_health_ledger(self, report: Dict[str, Any]):
        """
        持久化扫描结果到 MySQL ledger
        """
        try:
            pool = await MySQLPoolManager.get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 创建 Ledger 表
                    create_sql = """
                    CREATE TABLE IF NOT EXISTS stock_health_ledger (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        stock_code VARCHAR(20) NOT NULL UNIQUE,
                        status VARCHAR(10) NOT NULL,
                        listing_date DATE,
                        missing_count INT DEFAULT 0,
                        missing_details JSON,
                        suspension_count INT DEFAULT 0,
                        last_scan_time DATETIME,
                        repair_status INT DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_status (status),
                        INDEX idx_last_scan (last_scan_time)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """
                    await cursor.execute(create_sql)
                    
                    # 更新或插入记录
                    upsert_sql = """
                    INSERT INTO stock_health_ledger 
                    (stock_code, status, listing_date, missing_count, missing_details, suspension_count, last_scan_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        status = VALUES(status),
                        missing_count = VALUES(missing_count),
                        missing_details = VALUES(missing_details),
                        suspension_count = VALUES(suspension_count),
                        last_scan_time = VALUES(last_scan_time)
                    """
                    await cursor.execute(upsert_sql, (
                        report["stock_code"],
                        report["status"],
                        report["listing_date"],
                        report["missing_count"],
                        json.dumps(report["missing_dates"]),
                        report["suspension_count"],
                        report["check_time"]
                    ))
            # 只有异常时才打 Warning 日志
            if report["status"] == "ERROR":
                logger.warning(f"⚠️ 深度扫描发现异常: {report['stock_code']} 缺失 {report['missing_count']} 天")
        except Exception as e:
            logger.error(f"❌ 持久化 Ledger 失败: {e}")

    async def run_universe_scan_batch(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        运行全市场批量扫描
        """
        logger.info(f"开始执行全市场深度扫描迭代 (批次大小: {batch_size})")
        
        # 1. 获取需要扫描的股票代码
        pool = await MySQLPoolManager.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                # 0. 确保表存在
                create_sql = """
                CREATE TABLE IF NOT EXISTS stock_health_ledger (
                    stock_code VARCHAR(20) PRIMARY KEY,
                    status VARCHAR(10) NOT NULL,
                    listing_date DATE,
                    missing_count INT DEFAULT 0,
                    missing_details JSON,
                    suspension_count INT DEFAULT 0,
                    last_scan_time DATETIME,
                    repair_status INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_status (status),
                    INDEX idx_last_scan (last_scan_time)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """
                await cursor.execute(create_sql)

                # 策略：优先选最久没扫的，如果 ledger 还没覆盖全市场，则补充新发现的代码
                await cursor.execute("SELECT stock_code FROM stock_health_ledger ORDER BY last_scan_time ASC LIMIT %s", (batch_size,))
                stock_list = [r[0] for r in await cursor.fetchall()]
                
                if len(stock_list) < batch_size:
                    # 如果 ledger 还没满 batch_size，或者全市场代码还没进 ledger，则从 ClickHouse 捞取
                    needed = batch_size - len(stock_list)
                    async with self.clickhouse_pool.acquire() as ch_conn:
                        async with ch_conn.cursor() as ch_cursor:
                            # 捞取 ClickHouse 中的一部分代码作为种子
                            await ch_cursor.execute("SELECT DISTINCT stock_code FROM stock_kline_daily LIMIT 2000")
                            all_codes = [r[0] for r in await ch_cursor.fetchall()]
                            
                            # 找出不在 ledger 中的代码
                            await cursor.execute("SELECT stock_code FROM stock_health_ledger")
                            existing_in_ledger = {r[0] for r in await cursor.fetchall()}
                            
                            final_new_codes = []
                            for c in all_codes:
                                if c not in existing_in_ledger:
                                    final_new_codes.append(c)
                                    if len(final_new_codes) >= needed:
                                        break
                            
                            stock_list.extend(final_new_codes)
                
                logger.info(f"待处理股票列表 ({len(stock_list)} 只): {stock_list[:10]}{'...' if len(stock_list) > 10 else ''}")

        # 2. 依次扫描
        results = []
        error_count = 0
        
        for i, code in enumerate(stock_list):
            try:
                logger.info(f"[{i+1}/{len(stock_list)}] 正在深度扫描: {code}")
                report = await self.check_stock_health_deep(code)
                logger.info(f"[{i+1}/{len(stock_list)}] {code} 扫描完成，状态: {report['status']}")
                await self._persist_health_ledger(report)
                results.append(report)
                if report["status"] == "ERROR":
                    error_count += 1
            except Exception as e:
                logger.error(f"扫描股票 {code} 时发生致命错误: {e}", exc_info=True)
                
        return {
            "batch_size": len(stock_list),
            "scanned_count": len(results),
            "error_count": error_count,
            "message": f"扫描完成，发现 {error_count} 只异常股票"
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
        consistency = await self.check_cross_db_consistency(days=7)
        duplicates = await self.check_duplicates()
        
        # 汇总状态
        all_status = [timeliness["status"], consistency["status"], duplicates["status"]]
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
                "cross_db_consistency": consistency,
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
