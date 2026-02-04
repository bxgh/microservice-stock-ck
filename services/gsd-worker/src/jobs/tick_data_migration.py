import logging
import asyncio
import os
import aiomysql
import pytz
from datetime import datetime, timedelta
from core.clickhouse_client import ClickHouseClient
from gsd_shared.utils.calendar_service import CalendarService

logger = logging.getLogger(__name__)
CST = pytz.timezone('Asia/Shanghai')

async def check_audit_status(mysql_config, target_date_str: str) -> bool:
    """
    检查指定日期的 Gate-3 审计状态
    """
    conn = None
    try:
        conn = await aiomysql.connect(**mysql_config)
        async with conn.cursor() as cur:
            # 查询昨日 Gate-3 审计结果
            sql = "SELECT is_complete FROM alwaysup.data_gate_audits WHERE trade_date=%s AND gate_id='GATE_3'"
            await cur.execute(sql, (target_date_str,))
            row = await cur.fetchone()
            if row and row[0] == 1:
                logger.info(f"✅ 审计校验通过: {target_date_str} Gate-3 已完成")
                return True
            
            logger.error(f"❌ 审计校验失败: {target_date_str} Gate-3 尚未通过或不存在审计记录")
            return False
    except aiomysql.Error as e:
        logger.error(f"❌ 数据库操作异常: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 非预期异常，校验审计状态失败: {e}")
        return False
    finally:
        if conn:
            conn.close()

async def run():
    ch_client = ClickHouseClient()
    cal = CalendarService()
    
    # 获取数据库配置
    mysql_config = {
        "host": os.getenv("GSD_DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("GSD_DB_PORT", 36301)),
        "user": os.getenv("GSD_DB_USER", "root"),
        "password": os.getenv("GSD_DB_PASSWORD", "alwaysup@888"),
        "db": os.getenv("GSD_DB_NAME", "alwaysup"),
        "autocommit": True
    }
    
    try:
        # 1. 精准确定归档日期（回溯寻找最近一个交易日）
        current_date = datetime.now(CST).date()
        target_date = current_date - timedelta(days=1)
        while not cal.is_trading_day(target_date):
            target_date -= timedelta(days=1)
            
        target_date_str = target_date.strftime('%Y-%m-%d')
        logger.info(f"🚀 开始归档任务预检: 目标日期 = {target_date_str}")
        
        await ch_client.connect()
        
        # 2. 统计待迁移数据量 (作为非阻塞的第一步)
        count_sql = f"SELECT count() FROM stock_data.tick_data_intraday WHERE trade_date = '{target_date_str}'"
        row_count = ch_client.execute(count_sql)[0][0]
        
        # 3. 【核心安全检查】校验审计状态 (置于迁移操作之前，作为实质性的“准入”)
        audit_ok = await check_audit_status(mysql_config, target_date_str)
        if not audit_ok:
            force_run = os.getenv("FORCE_MIGRATION", "false").lower() == "true"
            if not force_run:
                logger.warning(f"⚠️ 审计校验未通过，跳过本次自动归档。请待审计完成后手动触发归档任务。")
                # 即使没归档，也按正常完成返回，不阻塞 Gate-1
                return 0
            logger.warning(f"⚠️ 审计未通过，但强制运行标识已启用，执行物理迁移...")

        if row_count == 0:
            logger.warning(f"⚠️ {target_date_str} 无分笔数据需要迁移。")
        else:
            # 4. 原子迁移数据
            insert_sql = f"""
            INSERT INTO stock_data.tick_data 
            SELECT * FROM stock_data.tick_data_intraday 
            WHERE trade_date = '{target_date_str}'
            """
            logger.info(f"正在将 {row_count} 条记录从当日表迁移至历史表...")
            ch_client.execute(insert_sql)
            logger.info("✅ 历史归档写入成功")
        
        # 5. 精准清理旧数据 (清理今日之前的所有旧数据)
        today_str = current_date.strftime('%Y-%m-%d')
        # 如果审计通过或强制运行，且迁移完成（或本就没数据），则执行清理
        cleanup_sql = f"ALTER TABLE stock_data.tick_data_intraday_local ON CLUSTER 'stock_cluster' DELETE WHERE trade_date < '{today_str}'"
        logger.info(f"正在执行物理清理 (WHERE trade_date < {today_str})...")
        ch_client.execute(cleanup_sql)
        
        logger.info("🎉 [Gate-1.0] 数据归档与当日表清理流程圆满完成")
        return 0
        
    except Exception as e:
        logger.error(f"❌ 归档任务异常: {e}", exc_info=True)
        return 1
    finally:
        ch_client.disconnect()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    exit_code = asyncio.run(run())
    import sys
    sys.exit(exit_code)
