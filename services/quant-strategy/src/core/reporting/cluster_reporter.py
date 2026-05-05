
"""
ClusterReporter 策略报告生成器

将分析结果转换为人类可读的 Markdown 报告。
"""
import logging
import os
from datetime import datetime
from typing import Any

from core.event_bus import EventBus

logger = logging.getLogger(__name__)

class ClusterReporter:
    """
    自动化分析报告模块
    """

    def __init__(self, output_dir: str = "docs/reports/clusters"):
        self.output_dir = output_dir
        # 确保路径是绝对路径
        if not os.path.isabs(self.output_dir):
            # 获取项目根目录 (假设在 src/core/reporting/ 下)
            root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
            self.output_dir = os.path.join(root, self.output_dir)

        os.makedirs(self.output_dir, exist_ok=True)
        self.bus = EventBus()

    async def initialize(self):
        """订阅事件"""
        self.bus.subscribe("market_analysis_completed", self.on_market_analysis_completed)
        logger.info(f"📊 ClusterReporter initialized, saving to {self.output_dir}")

    async def on_market_analysis_completed(self, event_data: dict[str, Any]):
        """事件回调"""
        trade_date = event_data.get("trade_date")
        report = event_data.get("report", [])
        if trade_date and report:
            await self.generate_daily_report(trade_date, report)

    async def generate_daily_report(self, trade_date: str, report_data: list[dict]):
        """
        生成每日聚类深度报告
        """
        if not report_data:
            logger.warning(f"No data to report for {trade_date}")
            return None

        filename = f"cluster_report_{trade_date}.md"
        file_path = os.path.join(self.output_dir, filename)

        md = []
        md.append(f"# 分笔量化策略 - 每日分析报告 ({trade_date})")
        md.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md.append(f"\n**聚类总数**: {len(report_data)}")

        md.append("\n## 1. 核心 Cluster 概览\n")
        md.append("| 簇ID | 成员数量 | 当前分歧度 | 趋势阶段 | 核心龙头 |")
        md.append("|---|---|---|---|---|")

        # 按成员数量排序显示 Top 10
        sorted_report = sorted(report_data, key=lambda x: x.get('count', len(x.get('members', []))), reverse=True)

        for item in sorted_report[:10]:
            cid = item.get('cluster_id', 'N/A')
            members = item.get('members', [])
            cnt = item.get('count', len(members))
            div = item.get('current_divergence', 0.0)
            phase = item.get('trend_phase', 'Steady')
            leaders = item.get('leaders', [])

            leader_str = "N/A"
            if leaders:
                leader_str = leaders[0][0] if isinstance(leaders[0], tuple) else str(leaders[0])

            md.append(f"| {cid} | {cnt} | {div:.3f} | {phase} | {leader_str} |")

        md.append("\n## 2. 重点 Cluster 深度洞察\n")

        for item in sorted_report[:5]: # 只详细列出规模最大的前 5 个
            cid = item.get('cluster_id')
            members = item.get('members', [])
            md.append(f"### Cluster {cid} - 详细分析")
            md.append(f"- **趋势判定**: {item.get('trend_phase', 'Steady')}")
            md.append(f"- **分歧度系数**: {item.get('current_divergence', 0.0):.4f}")
            md.append(f"- **核心成员样本**: {', '.join(members[:10])} {'...' if len(members) > 10 else ''}")

            md.append("\n#### 龙头影响力排序 (PageRank + OBI)")
            md.append("| 排名 | 股票代码 | 权重评分 |")
            md.append("|---|---|---|")
            leaders = item.get('leaders', [])
            for i, leader in enumerate(leaders[:5]):
                if isinstance(leader, tuple):
                    code, score = leader
                else:
                    code, score = leader, 1.0
                md.append(f"| {i+1} | {code} | {score:.4f} |")
            md.append("\n---")

        content = "\n".join(md)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"✅ Daily cluster report generated: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to write report file: {e}")
            return None

    async def close(self):
        self.bus.unsubscribe("market_analysis_completed", self.on_market_analysis_completed)
