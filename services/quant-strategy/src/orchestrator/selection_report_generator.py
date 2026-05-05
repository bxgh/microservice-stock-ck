"""
SelectionReportGenerator - 每日选股结果报告生成器
将 CandidatePoolService 的筛选结果转换为格式化的 Markdown 报表
"""
import os
import logging
from datetime import datetime
from typing import List, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class SelectionReportGenerator:
    """选股日报生成器"""
    
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            output_dir = os.getenv("SELECTION_REPORT_DIR")
        
        if output_dir is None:
            # 动态推导项目根目录 (src/orchestrator/selection_report_generator.py -> src -> project_root)
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, "docs/reports/daily/")
            
        self.output_dir = output_dir
        # 确保目录存在
        try:
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)
            logger.info(f"Report directory initialized: {self.output_dir}")
        except Exception as e:
            logger.warning(f"Could not create directory {self.output_dir} during init: {e}")

    def generate_daily_report(self, date: str, candidates: List[Any], pool_type: str = "long") -> str:
        """
        生成 MD 格式的选股日报内容
        :param date: 业务日期 (YYYY-MM-DD)
        :param candidates: Candidate 模型实例列表
        :param pool_type: 池子类型
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = "长线价值选股金股名单" if pool_type == "long" else "量化波段扫描报告"
        
        md = f"# 📊 {title} ({date})\n\n"
        md += f"- **生成时间**: `{now}`\n"
        md += f"- **策略模型**: `EPIC-002 Alpha Scoring Engine`\n"
        md += f"- **总扫描范围**: 全市场 A 股 (剔除 ST/黑名单/高风险)\n"
        md += f"- **有效入选数**: {len(candidates)} 只\n\n"
        
        md += "## 🏆 综合评分精英榜 (Top 10)\n\n"
        md += "| 排名 | 股票代码 | 综合分数 | 建议细分池 | 入选日期 |\n"
        md += "| :--- | :--- | :--- | :--- | :--- |\n"
        
        for idx, c in enumerate(candidates[:10], 1):
            date_str = c.entry_date.strftime('%Y-%m-%d') if hasattr(c, 'entry_date') and c.entry_date else "-"
            md += f"| {idx} | `{c.code}` | **{c.score:.2f}** | {c.sub_pool} | {date_str} |\n"
        
        md += "\n---\n"
        
        md += "## 🔍 策略逻辑说明\n"
        md += "1. **风控层 (Gate)**: 强制排除商誉占净资产 >30%、高质押率、及现金流收现比 <0.5 的标的。\n"
        md += "2. **价值层 (Value)**: 优先筛选 PEG < 1.0 的成长股，并结合行业中位 PE 进行安全边际修正。\n"
        md += "3. **品质层 (Quality)**: 基于 ROE 稳定度算法对“护城河”进行量化，平滑周期性波动。\n\n"
        
        md += "> [!IMPORTANT]\n"
        md += "> 注意: 本报告仅作为量化模型筛选参考，不构成投资建议。请结合大盘环境择机配置。数据源: AKShare/Internal DB.\n"
        
        # 保存文件
        file_name = f"{date}_{pool_type}_selection.md"
        file_path = os.path.join(self.output_dir, file_name)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md)
            logger.info(f"✅ 选股日报已保存至: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"❌ 保存日报失败: {str(e)}")
            return ""

# 导出实例供便捷使用
selection_report_generator = SelectionReportGenerator()
