"""
月度回测报告生成脚本
从 ClickHouse 读取 ads_l8_backtest_label 进行聚合统计。
"""
from clickhouse_driver import Client
import pandas as pd
import logging
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

TZ_SH = ZoneInfo("Asia/Shanghai")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CK_CONFIG = {
    'host': '127.0.0.1',
    'port': 9000,
    'user': 'default',
    'password': '',
    'database': 'stock_data'
}

def generate_report():
    client = Client(**CK_CONFIG)
    
    # 1. 整体胜率与收益统计 (T+5)
    query = """
        SELECT 
            anomaly_category,
            source_version,
            count() as sample_count,
            round(avg(ret_t5) * 100, 2) as avg_ret_5d_pct,
            round(avg(alpha_t5) * 100, 2) as avg_alpha_5d_pct,
            round(countIf(ret_t5 > 0) / count() * 100, 2) as win_rate_pct,
            round(countIf(alpha_t5 > 0) / count() * 100, 2) as alpha_rate_pct
        FROM ads_l8_backtest_label
        WHERE ret_t5 != 0 AND is_deleted = 0 -- 过滤未回填或停牌数据
        GROUP BY anomaly_category, source_version
        ORDER BY win_rate_pct DESC
    """
    
    logger.info("Fetching backtest statistics from ClickHouse...")
    stats = client.execute(query)
    
    # 转换为 DataFrame
    cols = ['anomaly_category', 'source_version', 'sample_count', 'avg_ret_5d_pct', 'avg_alpha_5d_pct', 'win_rate_pct', 'alpha_rate_pct']
    df = pd.DataFrame(stats, columns=cols)
    
    if df.empty:
        print("No backtest data available for report.")
        return

    # 2. 生成 Markdown 报告
    now = datetime.now(TZ_SH)
    report_date = now.strftime('%Y-%m-%d')
    report_md = f"# L8 异动信号回测月报 ({report_date})\n\n"
    report_md += "## 1. 核心指标统计 (T+5 周期)\n\n"
    report_md += "| 机制分类 | 版本 | 样本量 | 平均涨幅(%) | 平均超额(%) | 胜率(%) | 超额胜率(%) |\n"
    report_md += "|---|---|---|---|---|---|---|\n"
    
    for _, row in df.iterrows():
        report_md += f"| {row['anomaly_category']} | {row['source_version']} | {int(row['sample_count'])} | {row['avg_ret_5d_pct']}% | {row['avg_alpha_5d_pct']}% | {row['win_rate_pct']}% | {row['alpha_rate_pct']}% |\n"
    
    report_md += "\n> 注: 以上数据基于 ClickHouse ads_l8_backtest_label 聚合生成。\n"
    
    print("-" * 30)
    print(report_md)
    print("-" * 30)
    
    # 保存到文件
    report_path = f"docs/reports/anomaly_backtest_{now.strftime('%Y%m')}.md"
    # 注意: 这里在容器内运行，保存路径需要映射或手动处理
    # 我这里直接打印，实际使用时可以写入 artifacts
    
    return report_md

if __name__ == "__main__":
    generate_report()
