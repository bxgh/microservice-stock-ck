"""
StrategyOrchestrator - 策略编排器
串联 DAO, PeerSelector, DataLoader 和 Analyzers
实现完整的次新股多维对标策略逻辑
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .peer_selector import PeerSelector
from .data_loader import DataLoader
from src.analyzers.distribution import DistributionAnalyzer
from src.analyzers.ranking import RankingAnalyzer
from .ai_interpreter import AIInterpreter

logger = logging.getLogger(__name__)

class StrategyOrchestrator:
    """
    策略编排器 (GSF Part 3 核心)
    """
    
    def __init__(self):
        self.peer_selector = PeerSelector()
        self.data_loader = DataLoader()
        self.dist_analyzer = DistributionAnalyzer()
        self.rank_analyzer = RankingAnalyzer()
        self.ai_interpreter = AIInterpreter()
        
    async def run_analysis(
        self,
        target_code: str,
        current_date: str = None,
        days_lookback: int = 20,
        max_peers: int = 30
    ) -> Dict[str, Any]:
        """
        运行完整分析流程
        
        Args:
            target_code: 目标股票代码
            current_date: 当前分析日期 (YYYY-MM-DD), 默认为今天
            days_lookback: 回溯天数 (计算分布用的日期范围)
            max_peers: 最大同类股数量
            
        Returns:
            Dict: 包含所有分析结果的字典
        """
        logger.info(f"Starting analysis orchestration for {target_code}")
        
        # 1. 设置日期范围
        if not current_date:
            current_date = datetime.now().strftime('%Y-%m-%d')
            
        end_date = current_date
        start_date = (datetime.strptime(end_date, '%Y-%m-%d') - timedelta(days=days_lookback + 10)).strftime('%Y-%m-%d')
        
        try:
            # 2. 筛选同类股
            logger.info("Step 1: Selecting peers...")
            selection_result = await self.peer_selector.select_peers(target_code, max_peers=max_peers)
            peer_codes = selection_result.peers
            
            if not peer_codes:
                logger.warning(f"No peers found for {target_code}, focus only on target data")
            
            # 3. 加载特征数据
            logger.info(f"Step 2: Loading data for target and {len(peer_codes)} peers...")
            data_bundle = await self.data_loader.load_strategy_data(
                target_code, 
                peer_codes, 
                start_date, 
                end_date
            )
            
            target_df = data_bundle['target']
            peers_df = data_bundle['peers']
            
            if target_df.empty:
                return {"error": f"Target data for {target_code} not found"}
            
            # 4. 执行多维分布分析
            logger.info("Step 3: Running distribution analysis...")
            dist_results = self.dist_analyzer.analyze(target_df, peers_df)
            
            # 5. 执行排名分析
            logger.info("Step 4: Running ranking analysis...")
            rank_results = self.rank_analyzer.analyze(target_df, peers_df)
            
            # 6. 执行 AI 智能解读 (新增)
            logger.info("Step 5: Running AI interpretation...")
            ai_insight = await self.ai_interpreter.interpret(
                target_info={
                    "code": target_code,
                    "name": selection_result.target_name,
                    "industry": selection_result.target_ths_industry
                },
                distribution=dist_results,
                ranking=rank_results,
                peer_count=len(peer_codes)
            )
            
            # 7. 汇总结果
            final_report_data = {
                "target_info": {
                    "code": target_code,
                    "name": selection_result.target_name,
                    "industry": selection_result.target_ths_industry,
                    "core_concepts": selection_result.target_core_concepts
                },
                "peers": {
                    "count": len(peer_codes),
                    "method": selection_result.selection_method,
                    "list": peer_codes[:10]  # 只在概查中记录前10个
                },
                "analysis": {
                    "distribution": dist_results,
                    "ranking": rank_results,
                    "ai_insight": ai_insight.model_dump() if ai_insight else None
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Analysis completed for {target_code}")
            return final_report_data
            
        except Exception as e:
            logger.exception(f"Strategy execution failed for {target_code}: {e}")
            return {"error": str(e)}
