"""
ReportGenerator - 策略报告生成器
将分析结果转换为易读的 Markdown 格式报告
"""
import pandas as pd
from typing import Dict, Any, List

class ReportGenerator:
    """
    报告生成器
    输出结构化的 Markdown 分析报告
    """
    
    @staticmethod
    def generate_markdown(result: Dict[str, Any]) -> str:
        """生成 Markdown 报告内容"""
        if "error" in result:
            return f"# 战略分析报告 - 出错\n\n错误信息: {result['error']}"
            
        target = result['target_info']
        peers = result['peers']
        analysis = result['analysis']
        
        md = f"# 次新股多维对标分析报告: {target['name']} ({target['code']})\n\n"
        md += f"- **分析时间**: {result['timestamp']}\n"
        md += f"- **所属行业 (Ths L3)**: {target['industry']}\n"
        md += f"- **核心概念**: {', '.join(target['core_concepts']) if target['core_concepts'] else '无'}\n"
        md += f"- **对标样本数**: {peers['count']} (通过 {peers['method']} 筛选)\n\n"
        
        # 1. 最新对标分位点
        md += "## 1. 最新对标分位点 (Percentile)\n"
        md += "> 说明: 分位点越高(接近100)，表示在该维度上目标股强于越多同行。反之则较弱。\n\n"
        
        dist = analysis.get('distribution', {})
        if not dist:
            md += "*暂无分布数据*\n\n"
        else:
            # 取最新的一天
            latest_date = sorted(dist.keys())[-1]
            md += f"**日期**: {latest_date}\n\n"
            md += "| 特征维度 | 分位点 | 状态 |\n"
            md += "| :--- | :--- | :--- |\n"
            
            for feat, val in dist[latest_date].items():
                status = "强势" if val > 70 else ("弱势" if val < 30 else "中性")
                md += f"| {feat} | {val}% | {status} |\n"
            md += "\n"
            
        # 2. 详细排名情况
        md += "## 2. 核心特征排名\n\n"
        ranking = analysis.get('ranking', {})
        if not ranking:
            md += "*暂无排名数据*\n\n"
        else:
            latest_date = sorted(ranking.keys())[-1]
            data = ranking[latest_date]
            
            md += "| 特征维度 | 排名 | 前三名对手 |\n"
            md += "| :--- | :--- | :--- |\n"
            
            for feat, rank_str in data['rankings'].items():
                # 获取前3名
                tops = [f"{p['ts_code']}({p[feat]:.2f})" for p in data['top_peers'].get(feat, [])[:3]]
                md += f"| {feat} | {rank_str} | {', '.join(tops)} |\n"
            md += "\n"
            
        # 3. AI 智能解读 (新增)
        ai_insight = analysis.get('ai_insight')
        if ai_insight:
            md += "## 3. AI 专家级深度解读\n"
            md += f"> **核心综述**: {ai_insight['summary']}\n\n"
            
            md += "### 盘口特征洞察\n"
            for insight in ai_insight['insights']:
                md += f"- **{insight['feature_id']}**: {insight['observation']}  \n"
                md += f"  *解读: {insight['implication']}*\n"
            md += "\n"
            
            md += "### 市场状态判别\n"
            regime = ai_insight['regime']
            md += f"- **当前状态**: `{regime['regime_name']}` (置信度: {regime['confidence']*100:.1f}%)\n"
            md += f"- **深度分析**: {regime['description']}\n\n"
            
            md += "### 专家指导建议\n"
            advice = ai_insight['advice']
            md += f"- **建议动作**: **{advice['action']}**\n"
            md += f"- **核心逻辑**: {advice['reason']}\n\n"
        else:
            # 兼容旧逻辑
            md += "## 3. 策略初步建议\n\n"
            good_count = 0
            latest_date = sorted(dist.keys())[-1] if dist else None
            if dist and latest_date in dist:
                 good_count = sum(1 for v in dist[latest_date].values() if v > 70)
            
            if good_count >= 5:
                md += "**[建议] 重点关注** - 该股在大多数技术维度上显著优于同类对标股票，可能存在补涨或超强溢价机会。\n"
            elif good_count >= 2:
                md += "**[建议] 中性观察** - 该股具有部分强势特征，建议结合市场热度进行择时。\n"
            else:
                md += "**[建议] 谨慎操作** - 该股多数维度处于同类股中下游水平，存在低估可能，但也可能面临估值出清压力。\n"
            
        return md
